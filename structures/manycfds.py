import copy
import safir_tools
import shutil
import sys
import os

"""Reviewed version of manycfds.py script by zarooba01"""

"""To be implemented:
    1) GiD directory tree;
    2) check for integrity of thermal results: if all BEAM elements were calculated NG times (2 as a default)
    3) another object named BeamType or Section - use it to operate on thermal input files and to store its attributes
    (paths, original and newbeamtype etc.) and methods (like change_in() or run())
    4) finding elements within domain with their exact (according to the integration point) locations
    5) taking arguments with flags in console mode (-c/---config, -t/--transfer etc.)
    
    ~kowalskiw~"""


def change_in(inFile, thermal_in_file):
    # new beam type is old + original beam types number + 1 (starts with 1 not 0)
    newbeamtype = 1 + inFile.beamparameters['beamtypes'].index(os.path.basename(thermal_in_file)[4:-3]) + \
                  len(inFile.beamparameters['beamtypes'])
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

    # write changed file
    with open(thermal_in_file, 'w') as file:
        file.writelines(init)


class ManyCfds:
    def __init__(self, config_dir, transfer_dir, mechanical_input_file, safir_exe_path):
        self.config_dir = config_dir
        self.transfer_dir = transfer_dir
        self.mechanical_input_file = mechanical_input_file
        self.safir_exe_path = safir_exe_path
        self.working_dir = os.path.dirname(mechanical_input_file)

        self.inFile_backup = self.get_info_from_infile()
        self.inFile = self.get_info_from_infile()

        self.cfd_thermal_infiles = self.get_all_thermal_infiles()

    def main(self):
        self.add_rows()  # doubling beam types with cfd version of each section
        self.double_beam_num()  # doubling beam types number
        self.copy_files()  # copying sections with adding 'cfd_' prefix
        self.change_in_for_infiles()  # modify thermal attack in all 'cfd_*.IN' from FISO to CFD
        # iterate over transfer files and calculate elements within each domain
        for i, transfer_file in enumerate(os.listdir(self.transfer_dir)):
            if self.operate_on_cfd(transfer_file):
                self.run_safir_for_all_thermal(i)

    def get_info_from_infile(self):
        """
        InFile object is created based on *.in file
        """
        with open(self.mechanical_input_file, 'r+') as file:
            self.inFile = safir_tools.InFile('dummy', file.readlines())

        return self.inFile

    def add_rows(self):
        """
            Doubling rows in beamparameters in inFile.file_lines and adding 'cfd_' before beam name
        """
        start = self.inFile.beamparameters['index'] + 1  # the line where beamparameters starts in inFile.file_lines
        end = self.inFile.file_lines.index('END_TRANS\n')  # start + self.inFile.beamparameters['beamnumber'] * 3
        data_add = self.inFile.file_lines[start:end]
        for num in range(len(data_add)):
            if data_add[num].endswith('.tem\n'):
                data_add[num] = 'cfd_' + data_add[num]
        self.inFile.file_lines.insert(end, ''.join(data_add))

    def double_beam_num(self):
        line_params = self.inFile.file_lines[self.inFile.beamparameters['beamline']].split()
        line_param_num = line_params[2]
        doubled_param = str(int(line_param_num) * 2)
        newbemline = ' '.join((line_params[0], line_params[1], doubled_param, '\n'))
        self.inFile.file_lines[self.inFile.beamparameters['beamline']] = newbemline

    def copy_files(self):
        """ NAME CHANGE AND COPYING FILES"""
        for beam in self.inFile.beamparameters['beamtypes']:
            try:
                shutil.copyfile(os.path.join(self.config_dir, f'{beam}.IN'),
                                os.path.join(self.working_dir, f'cfd_{beam}.IN'))
            except FileNotFoundError as e:
                print(e)
                sys.exit(1)

    def get_all_thermal_infiles(self):
        return ['cfd_' + beam + '.in' for beam in self.inFile.beamparameters['beamtypes']]

    def change_in_for_infiles(self):
        for thermal_infile in self.cfd_thermal_infiles:
            change_in(self.inFile, os.path.join(self.working_dir, thermal_infile))

    def operate_on_cfd(self, transfer_file):
        actual_file = os.path.join(self.transfer_dir, transfer_file)
        domain = find_transfer_domain(actual_file)
        shutil.copyfile(actual_file, os.path.join(self.working_dir, 'cfd.txt'))

        inFileCopy = copy.deepcopy(self.inFile)
        beamparams = inFileCopy.beamparameters
        file_lines = inFileCopy.file_lines
        """
        ADDING ELEMENTS INSIDE DOMAIN
        """
        elements_inside_domain = []
        for element in inFileCopy.beams:

            first_node_id = element[1]
            last_node_id = element[3]
            first_node_coor = inFileCopy.nodes[first_node_id - 1][1:]
            last_node_coor = inFileCopy.nodes[last_node_id - 1][1:]

            # enable elements to be partially within domain (only start or end point is enough)
            if ((domain[1] > first_node_coor[0] > domain[0] or domain[1] > last_node_coor[0] > domain[0])
                    and (domain[3] > first_node_coor[1] > domain[2] or domain[3] > last_node_coor[1] > domain[2])
                    and (domain[5] > first_node_coor[2] > domain[4] or domain[5] > last_node_coor[2] > domain[4])):
                elements_inside_domain.append(element[0])

        print(f'[INFO] There are {len(elements_inside_domain)} BEAM elements located in the {domain} domain:')

        if len(elements_inside_domain) == 0:
            return False
        else:
            print(f'{elements_inside_domain}')

        """
        CHANGING BEAM ID AT END OF THE LINE
        """
        lines = 0
        for line in file_lines[beamparams['elemstart']:]:
            elem_data = line.split()
            if 'ELEM' not in line:
                break
            if int(elem_data[1]) in elements_inside_domain:
                actual_line = beamparams['elemstart'] + lines
                new_beam_number = int(elem_data[-1]) + beamparams['beamnumber']
                file_lines[actual_line] = f'  \t{"    ".join(elem_data[:-1])}\t{new_beam_number}\n'
            lines += 1

        # save modified mechanical input file as 'dummy.in'
        with open(os.path.join(self.working_dir, 'dummy.in'), 'w') as f:
            for line in file_lines:
                f.write(line)

        return True

    def run_safir_for_all_thermal(self, iteration):
        for file_in in self.cfd_thermal_infiles:
            file = os.path.join(self.working_dir, file_in)
            safir_tools.run_safir(file, self.safir_exe_path, fix_rlx=False)
            [os.rename(f'{file[:-3]}.{e}', f'{file[:-3]}_{iteration}.{e}') for e in ['XML', 'OUT']]


def find_transfer_domain(transfer_file):
    r = False
    all_x, all_y, all_z = [], [], []
    with open(transfer_file) as file:
        for line in file:
            if r:
                try:
                    x, y, z = line.split()
                except ValueError:
                    break
                all_x.append(x)
                all_y.append(y)
                all_z.append(z)
            if 'XYZ_INTENSITIES' in line:
                r = True
    all_x = [float(x) for x in all_x]
    all_y = [float(x) for x in all_y]
    all_z = [float(x) for x in all_z]
    domain = [min(all_x), max(all_x), min(all_y), max(all_y), min(all_z), max(all_z)]

    # transfer domain boundaries
    return domain  # [XA, XB, YA, YB, ZA, ZB]


if __name__ == '__main__':

    arguments = sys.argv[1:]
    for i, a in enumerate(arguments):
        arguments[i] = os.path.abspath(a)
    manycfds = ManyCfds(*arguments)
    manycfds.main()
