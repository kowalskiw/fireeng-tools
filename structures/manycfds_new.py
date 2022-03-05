import copy
import safir_tools
import shutil
import sys
import os
import argparse as ar
from file_read_backwards import FileReadBackwards as frb


class ManyCfds:
    def __init__(self, config_dir, transfer_dir, mechanical_input_file, safir_exe_path):
        self.config_dir = config_dir
        self.transfer_dir = transfer_dir
        self.mechanical_input_file = mechanical_input_file
        self.safir_exe_path = safir_exe_path
        self.working_dir = os.path.dirname(mechanical_input_file)

        self.beamtypes = []
        self.transfer_files = []

    def main(self):



        #mechinfile = MechInFile("D:\\ConsultRisk\\testowe\\test_05_03\\manycfds\\my_sim\\beam.in")
        mechinfile = MechInFile("D:\\ConsultRisk\\testowe\\test_05_03\\manycfds\\my_sim\\beam.in")
        self.beamtypes = mechinfile.beamparameters['beamtypes']

        self.copy_files()  # copying sections with adding 'cfd_' prefix

    def copy_files(self):
        """ NAME CHANGE AND COPYING FILES"""
        for beam in self.beamtypes:
            try:
                shutil.copyfile(os.path.join(self.config_dir, f'{beam}.IN'),
                                os.path.join(self.working_dir, f'cfd_{beam}.IN'))
            except FileNotFoundError as e:
                print(e)
                sys.exit(1)

    def get_all_transfer_files(self):


class MechInFile(safir_tools.InFile):
    def __init__(self, mechanical_input_file):
        #self.mechanical_input_file = mechanical_input_file
        with open(mechanical_input_file) as file:
            super().__init__('dummy', file.readlines())

        self.beamline = self.beamparameters['BEAM']
        self.start_beams_line = self.beamparameters['NODOFBEAM']
        self.end_beams_line = self.beamparameters['END_TRANS_LAST']

    def main(self):
        self.add_rows()  # doubling beam types with cfd version of each section
        self.double_beam_num()  # doubling beam types number
        self.save_file(self.file_lines)

    def add_rows(self):
        """Doubling rows in beamparameters in inFile.file_lines and adding 'cfd_' before beam name"""
        data_add = self.file_lines[self.beamparameters['NODOFBEAM']+1:self.beamparameters['END_TRANS_LAST']]
        for num in range(len(data_add)):
            if data_add[num].endswith('.tem\n'):
                data_add[num] = 'cfd_' + data_add[num]
        self.file_lines.insert(self.beamparameters['END_TRANS_LAST'], ''.join(data_add))

    def double_beam_num(self):
        line_params = self.file_lines[self.beamline].split()
        line_param_num = line_params[2]
        doubled_param = str(int(line_param_num) * 2)
        newbemline = ' \t '.join(("    ", line_params[0], line_params[1], doubled_param, '\n'))
        self.file_lines[self.beamline] = newbemline

    def save_file(self, lines):
        with open("newtest.in", "w") as file:
            file.writelines(lines)


class Section:
    def __init__(self, transfer_file):
        self.transfer_file = transfer_file
        self.domain = self.find_transfer_domain()

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


    def find_transfer_domain(self):
        r = False
        all_x, all_y, all_z = [], [], []
        with open(self.transfer_file) as file:
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





def get_arguments():
    parser = ar.ArgumentParser(description='Run many cfds')
    parser.add_argument('-c', '--config_dir', help='Path to configuration directory', required=True)
    parser.add_argument('-t', '--transfer_dir', help='Path transfer directory', required=True)
    parser.add_argument('-m', '--mechanical_input_file', help='Mechanical input file', required=True)
    parser.add_argument('-s', '--safir_exe_path', help='Path to SAFIR executable', default='/safir.exe')
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    args = get_arguments()
    for key, value in args.__dict__.items():
        args.__dict__[key] = os.path.abspath(value)

    manycfds = ManyCfds(**args.__dict__)
    manycfds.main()



