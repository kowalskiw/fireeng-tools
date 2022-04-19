import copy
import safir_tools
import shutil
import sys
import os
import argparse as ar
from file_read_backwards import FileReadBackwards as frb
from decimal import Decimal as dec


class ManyCfds:
    def __init__(self, config_dir, transfer_dir, mechanical_input_file, safir_exe_path):
        self.config_dir = config_dir
        self.transfer_dir = transfer_dir
        self.mechanical_input_file = mechanical_input_file
        self.safir_exe_path = safir_exe_path
        self.working_dir = os.path.dirname(mechanical_input_file)

        self.transfer_files = []
        self.all_thermal_infiles = []

        self.mechinfile = MechInFile(self.mechanical_input_file)
        self.beamtypes = self.mechinfile.beamparameters['beamtypes']

        self.all_sections = []

    def main(self):
        self.copy_files()  # copying sections with adding 'cfd_' prefix
        self.get_all_transfer_files()
        self.change_in_for_infiles()
        self.run_section()

        #self.show_domains()

    def copy_files(self):
        """ NAME CHANGE AND COPYING FILES + adding thermal infiles to the list self.all_thermal_infiles"""
        for beam in self.beamtypes:
            try:
                infile = f'cfd_{beam}.IN'
                shutil.copyfile(os.path.join(self.config_dir, f'{beam}.IN'),
                                os.path.join(self.working_dir, f'cfd_{beam}.IN'))
                self.all_thermal_infiles.append(infile)

            except FileNotFoundError as e:
                print(e)
                sys.exit(1)

    def change_in(self, thermal_in_file):
        """
        CHANGING PARAMETERS IN thermal.in files e.g cfd_ipe600.in
        new beam type is old + original beam types number + 1 (starts with 1 not 0)

        beamtypes = ['ipe600_1', 'ipe600_3', 'ipe600_2']
        base(thermal_in_file) = cfd_ipe600_3.IN
        """

        newbeamtype = self.beamtypes.index(os.path.basename(thermal_in_file)[4:-3]) + len(self.beamtypes) +1
        # open thermal analysis input file
        with open(thermal_in_file) as file:
            init = file.readlines()

        # save backup of input file
        with open(f'{thermal_in_file}.bak', 'w') as file:
            file.writelines(init)

        # make changes
        for no in range(len(init)):
            line = init[no]
            # type of calculation
            if line == 'MAKE.TEM\n':
                init[no] = 'MAKE.TEMCD\n'

                # insert beam type
                [init.insert(no + 1, i) for i in ['BEAM_TYPE {}\n'.format(newbeamtype), '{}.in\n'.format('dummy')]]

            # change thermal attack functions
            elif line.startswith('   F  ') and 'FISO' in line:  # choose heating boundaries with FISO or FISO0 frontier
                # change FISO0 to FISO
                if 'FISO0' in line:
                    line = 'FISO'.join(line.split('FISO0'))

                # choose function to be changed with
                thermal_attack = 'CFD'

                if 'F20' not in line:
                    init[no] = 'FLUX {}'.format(thermal_attack.join(line[4:].split('FISO')))
                else:
                    init[no] = 'FLUX {}'.format('NO'.join((thermal_attack.join(line[4:].split('FISO'))).split('F20')))
                    init.insert(no + 1, 'NO'.join(line.split('FISO')))

            # change convective heat transfer coefficient of steel to 35 in locafi mode according to EN1991-1-2
            elif 'STEEL' in line:
                init[no + 1] = '{}'.format('35'.join(init[no + 1].split('25')))

            # change T_END
            elif ('TIME' in line) and ('END' not in line):
                try:
                    init[no + 1] = '    '.join([init[no + 1].split()[0], str(self.mechinfile.t_end), '\n'])
                except IndexError:
                    pass

        # write changed file
        with open(thermal_in_file, 'w') as file:
            file.writelines(init)

    def change_in_for_infiles(self):
        for thermal_infile in self.all_thermal_infiles:
            self.change_in(os.path.join(self.working_dir, thermal_infile))

    def get_all_transfer_files(self):
        """ adding all transfer files to transfer_files list"""
        for filename in os.listdir(self.transfer_dir):
            transfer_file = os.path.join(self.transfer_dir, filename)
            self.transfer_files.append(transfer_file)


    def run_section(self):
        """Create object based on transfer file"""
        for transfer_file in self.transfer_files:
            sect = Section(transfer_file,  self.mechinfile, self.working_dir, self.all_thermal_infiles, self.safir_exe_path)
            self.all_sections.append(sect)


    def show_domains(self):
        for i in self.all_sections:
            print(i.domain)


class MechInFile(safir_tools.InFile):
    def __init__(self, mechanical_input_file):
        with open(mechanical_input_file) as file:
            super().__init__('dummy', file.readlines())

        self.beamline = self.beamparameters['BEAM']
        self.start_beams_line = self.beamparameters['NODOFBEAM']
        self.end_beams_line = self.beamparameters['END_TRANS_LAST']
        self.main()

    def main(self):
        self.add_rows()  # doubling beam types with cfd version of each section
        self.double_beam_num()  # doubling beam types number


    def add_rows(self):
        """Doubling rows in beamparameters in inFile.file_lines and adding 'cfd_' before beam name"""
        data_add = self.file_lines[self.beamparameters['NODOFBEAM']+1:self.beamparameters['END_TRANS_LAST']]
        for num in range(len(data_add)):
            if data_add[num].endswith('.tem\n'):
                data_add[num] = 'cfd_' + data_add[num]
        self.file_lines.insert(self.end_beams_line, ''.join(data_add))

    def double_beam_num(self):
        """Doubling beam number in BEAM line"""
        line_params = self.file_lines[self.beamline].split()
        line_param_num = line_params[2]
        doubled_param = str(int(line_param_num) * 2)
        newbemline = ' \t '.join(("    ", line_params[0], line_params[1], doubled_param, '\n'))
        self.file_lines[self.beamline] = newbemline


class Section:
    def __init__(self, transfer_file, inFile, working_dir, thermal_files, safir_exe_path):
        self.transfer_file = transfer_file
        self.inFile = inFile
        self.inFileCopy = copy.deepcopy(self.inFile)
        self.btypes_in_domain = []
        self.file_lines = self.inFileCopy.file_lines
        self.beamparams = self.inFileCopy.beamparameters
        self.working_dir = working_dir
        self.thermal_files = thermal_files
        self.safir_exe_path = safir_exe_path
        self.domain = TransferDomain(self.transfer_file).find_transfer_domain()

        self.main()

    def main(self):
        self.repair_cfdtxt()
        self.copy_to_working_dir()
        self.elements_inside_domain = self.find_elements_inside_domain(self.inFileCopy)
        self.change_endline_beam_id()
        self.save_as_dummy()
        self.run_safir_for_all_thermal()

        inFileCopy = copy.deepcopy(self.inFile)


    def repair_cfdtxt(self):
        ch_nsteps = False
        new_lines = []
        count_steps = -3
        read_time = 0
        t_end = -1

        # extract numbers from lines
        def numb_from_line(l, type=float):
            try:
                if type == float:
                    return float(''.join(l.split()))
                else:
                    return int(''.join(l.split()))
            except ValueError:
                print(f'errored value: "{l}"')
                exit(-1)

        # find two last time steps in the transfer file
        with frb(self.transfer_file, encoding='utf-8') as backward:
            # getting lines by lines starting from the last line up
            for line in backward:

                if 'TIME' in line:
                    read_time = 1 if read_time == 0 else 2

                if read_time == 1:
                    t_end = numb_from_line(previous)
                    read_time = -1
                elif read_time == 2:
                    interval = t_end - numb_from_line(previous)
                    break

                previous = line

        nsteps = int(t_end / interval) + 1  # number of time steps present in the transfer file

        # check if the number of time steps in file is consistent with specified in the transfer file preamble
        with open(self.transfer_file) as file:
            for line in file:
                if 'NP' in line:
                    ch_nsteps = False

                #
                if ch_nsteps:
                    count_steps += 1
                    if count_steps == -2:
                        # check if NSTEPS is OK
                        if numb_from_line(line, type=int) == nsteps:
                            return 0

                        new_lines.append(f'    {nsteps}\n')
                        continue
                    if count_steps > nsteps:
                        continue

                if 'NSTEPS' in line:
                    ch_nsteps = True

                new_lines.append(line)

        # overwrite invalid file
        with open(self.transfer_file, 'w') as file:
            file.writelines(new_lines)

    def copy_to_working_dir(self):
        """copy transfer file as cfd.txt to working dir"""
        shutil.copyfile(self.transfer_file, os.path.join(self.working_dir, 'cfd.txt'))

    def find_elements_inside_domain(self, inFileCopy):
        elements_inside_domain = []
        for element in inFileCopy.beams:

            first_node_id = element[1]
            last_node_id = element[3]
            first_node_coor = inFileCopy.nodes[first_node_id - 1][1:]
            last_node_coor = inFileCopy.nodes[last_node_id - 1][1:]

            # enable elements to be partially within domain (only start or end point is enough)
            if ((self.domain[1] > first_node_coor[0] > self.domain[0] or self.domain[1] > last_node_coor[0] > self.domain[0])
                    and (self.domain[3] > first_node_coor[1] > self.domain[2] or self.domain[3] > last_node_coor[1] > self.domain[2])
                    and (self.domain[5] > first_node_coor[2] > self.domain[4] or self.domain[5] > last_node_coor[2] > self.domain[4])):
                elements_inside_domain.append(element[0])

        print(f'[INFO] There are {len(elements_inside_domain)} BEAM elements located in the {self.domain} domain:')

        if len(elements_inside_domain) == 0:
            return False
        else:
            print(f'{elements_inside_domain}')
        return elements_inside_domain

    def change_endline_beam_id(self):

        lines = 0
        for line in self.file_lines[self.beamparams['elem_start']:]:
            elem_data = line.split()
            if 'ELEM' not in line or 'RELAX' in line:
                break
            if int(elem_data[1]) in self.elements_inside_domain:
                actual_line = self.beamparams['elem_start'] + lines
                new_beam_number = int(elem_data[-1]) + self.beamparams['beamnumber']

                # add the beam type to be calculated
                try:
                    self.btypes_in_domain.index(int(elem_data[-1]) - 1)
                except ValueError:
                    self.btypes_in_domain.append(int(elem_data[-1]) - 1)

                self.file_lines[actual_line] = f'  \t{"    ".join(elem_data[:-1])}\t{new_beam_number}\n'
            lines += 1

    def save_as_dummy(self):
        with open(os.path.join(self.working_dir, 'dummy.in'), 'w') as f:
            for line in self.file_lines:
                f.write(line)

    def run_safir_for_all_thermal(self):
        for thermal_file in self.thermal_files:
            file = os.path.join(self.working_dir, thermal_file)
            print(f'\n >>>> {os.path.basename(self.transfer_file)} <<<<<')
            safir_tools.run_safir(file, self.safir_exe_path, fix_rlx=False)
            """
            #[os.rename(f'{file[:-3]}.{e}', f'{file[:-3]}_{iteration}.{e}') for e in ['XML', 'OUT']]
            while True:
                try:
                    [os.rename(f'{file[:-3]}.{e}', f'{file[:-3]}_{iteration}.{e}') for e in ['XML', 'OUT']]
                    break
                except FileExistsError:
                    iteration = str(iteration) + 'a'
            """

class TransferDomain:

    def __init__(self, transfer_file):
        self.transfer_file = transfer_file
        self.domain = self.find_transfer_domain()

    def find_transfer_domain(self):
        def size(data):
            data.sort()
            return abs(data[1] - data[0])

        def minmax(values: list, cell_size: float = 0):
            return float(min(values) - cell_size / 2), float(max(values) + cell_size / 2)

        r = False
        axes = [[], [], []]
        domain = []

        with open(self.transfer_file) as file:
            for line in file:
                spltd = line.split()
                if r:
                    if len(spltd) != 3:
                        break
                    [axes[i].append(v) if v not in axes[i] else None for i, v in enumerate(spltd)]
                elif 'XYZ_INTENSITIES' in line:
                    r = True

        axes = [[dec(axis[i]) for i in range(len(axis))] for axis in axes]
        try:
            cellsizes = [size(axis) for axis in axes]
        except IndexError:
            return []  # return empty list if transfer domain is flat

        [[domain.append(j) for j in minmax(axes[i], cell_size=cellsizes[i])] for i in range(3)]

        # transfer domain boundaries
        return domain  # [XA, XB, YA, YB, ZA, ZB]





def get_arguments():
    parser = ar.ArgumentParser(description='Run many cfds')
    parser.add_argument('-c', '--config_dir', help='Path to configuration directory', required=True)
    parser.add_argument('-t', '--transfer_dir', help='Path transfer directory', required=True)
    parser.add_argument('-m', '--mechanical_input_file', help='Mechanical input file', required=True)
    parser.add_argument('-s', '--safir_exe_path', help='Path to SAFIR executable', default='/safir.exe')
    args = parser.parse_args()

    return args

def get_arguments_dir():
    parser = ar.ArgumentParser(description='Run many cfds in dir')
    parser.add_argument('-s', '--safir_exe_path', help='Path to SAFIR executable', default='/safir.exe')
    #parser.add_argument('-m', '--mechanical_input_file', help='Mechanical input file', required=True)
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    try:
        """Giving all parameters by hand"""
        args = get_arguments()
        for key, value in args.__dict__.items():
            args.__dict__[key] = os.path.abspath(value)
        manycfds = ManyCfds(**args.__dict__)
        manycfds.main()

    except:
        """Run program in directory. Directory has to look alike:
            \config
            \my_sim   (that contains .in file) --- that dir can be sent as a parameter- maybe it's better solution
            \\transfer
        """
        args = get_arguments_dir()
        config_dir = os.path.join(os.getcwd(), "config")
        transfer_dir = os.path.join(os.getcwd(), "transfer")
        my_sim = os.path.join(os.getcwd(), "my_sim")
        dir_list = os.listdir(my_sim)
        #dir_list = os.listdir(args.__dict__["mechanical_input_file"])
        mech_in = os.path.join(my_sim, [x for x in dir_list if x.endswith("in") or x.endswith("IN")][0])
        manycfds = ManyCfds(config_dir, transfer_dir, mech_in, args.__dict__["safir_exe_path"])
        manycfds.main()

