from file_read_backwards import FileReadBackwards as frb
from sys import argv

class Part:
    def __init__(self, radf_txt_path, override=True):
        self.transfer_file = radf_txt_path

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
        print('Loading RADF file...', end='\r')
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

        print('Editing RADF file...', end='\r')
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
        print('Saving RADF file...', end='\r')
        with open(self.transfer_file, 'w') as file:
            file.writelines(new_lines)


pf = Part(argv[1])
pf.repair_cfdtxt()
print('[OK] RADF file repaired!')
