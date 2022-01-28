import sys
from file_read_backwards import FileReadBackwards as FRB
from os.path import abspath


def repair_cfdtxt(radffile):
    ch_nsteps = False
    new_lines = []
    count_steps = -3
    read_time = 0
    t_end = -1

    def numb_from_line(l, type='f'): 
        try:
            if type == 'f':
                return float(''.join(l.split()))
            else:
                return int(''.join(l.split()))
        except ValueError:
            print (f'errored value: "{l}"')
            exit(-1)

    with FRB(radffile, encoding='utf-8') as backward:
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
            
    nsteps = int(t_end / interval) + 1
    
    with open(radffile) as file:
        for line in file:
            if 'NP' in line:
                ch_nsteps = False
            
            if ch_nsteps:
                count_steps += 1
                if count_steps == -2:
                    new_lines.append(f'    {nsteps}\n')
                    continue
                if count_steps > nsteps:
                    continue
                
            if 'NSTEPS' in line:
                ch_nsteps = True
            
            new_lines.append(line)
             
    with open(f'{radffile.split(".txt")[0]}_part.txt', 'w') as file:
        file.writelines(new_lines)


repair_cfdtxt(abspath(sys.argv[1]))
exit(0)
            