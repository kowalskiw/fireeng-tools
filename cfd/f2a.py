from os import scandir
from os.path import abspath
from subprocess import run
import pandas as pd

from safir_tools import read_in, run_safir


class FDS2ASCII:
    def __init__(self, chid='', filetype=0, samp_fact=0, domain='', bounds='', time='', orient=0, variables=None,
                 inp='input.txt', out=''):
        if variables is None:
            variables = [1]
        self.chid = chid  # Enter Job ID string (CHID)
        self.filetype = filetype  # What type of file to parse? | PL3D file? Enter 1 | SLCF file? Enter 2 | BNDF file? Enter 3
        self.samp_factor = samp_fact   # Enter Sampling Factor for Data? (1 for all data, 2 for every other point, etc.)
        self.domain = domain   # Limit the domain size? (y or n)
        self.bounds = bounds  # Enter min/max x, y and z
        self.time = time  # Enter starting and ending time for averaging (s)
        self.orientation = orient    # Enter orientation: (plus or minus 1, 2 or 3)
        self.variables = variables  # Enter boundary file index for variables # Enter number of variables
        self.output = out  # Enter output file name
        self.input = inp

        self.c = []

    def build_config(self):
        self.c = [self.chid]
        self.c.append(self.filetype)
        if self.filetype == 1:
            print(f'PL3D is not supported yet')
            return -1
        elif self.filetype == 2:
            self.c.append(self.samp_factor)
            self.c.append(self.domain)
            if 'a' in self.domain.lower():
                print(f'"a" domain type is not supported yet')
                return -1
            elif self.domain.lower() == 'y':
                self.c.append(self.bounds)
            elif self.domain.lower() == 'n':
                pass
            else:
                raise ValueError(f'{self.domain} domain is not supported')
            self.c.append(self.time)
            self.c.append(len(self.variables))
            self.c.extend(self.variables)
            self.c.append(self.output)
        elif self.filetype == 3:
            print(f'BNDF is not supported yet')
            return -1
        else:
            raise ValueError(f'{self.filetype} number is not supported')

    def save_config(self):
        print(self.c)
        with open(self.input, 'w+') as fds_input:
            for e in self.c:
                fds_input.write(f'{e}\n')

    def run_f2a(self):
        run(f'fds2ascii < {self.input}',  shell=True)


class TempLayer:
    def __init__(self, bounds=None):
        if bounds is None:
            bounds = [[0, 0], [0, 0]]
        self.bounds = bounds
        self.temp_time = [[0, 0]]
        self.name = f'f_{self.bounds[0][0]}-{self.bounds[0][1]}_{self.bounds[1][0]}-{self.bounds[1][1]}'

    def tt_from_df(self, data):
        layer_df = pd.DataFrame()
        layer_df.append(data[(self.bounds[0][0] < data['Y']) &
                             (data['Y'] < self.bounds[0][1]) &
                             (self.bounds[1][0] < data['Z']) &
                             (data['Z'] < self.bounds[1][1])])

        for i, t in data.iloc[2:, 1:].iteritems():
            timestep = []
            for j, cell in t.iterrows():
                if cell > 20.5:
                   timestep.append(t)
            try:
                self.temp_time.append([i, sum(timestep) / len(timestep)])
            except ZeroDivisionError:
                self.temp_time.append([i, 20])

    def save_function(self, name=None):
        n = self.name if not name else name
        with open(n) as file:
            file.writelines([f'{i[0]}\t{i[1]}' for i in self.temp_time])

    def prepare4safir(self, structure):
        parameters = structure.beamparameters
        profiles = parameters['beamtypes']
        file_lines = structure.file_lines

        def modify_tem(profile):
            with open(f'{profile}.tem') as file:
                init = file.readlines()

            # make changes
            for no, line in enumerate(init):
                # change thermal attack functions
                if line.startswith('   F  ') and 'FISO' in line:  # choose heating boundaries with FISO or FISO0 front
                    # replace FISO0 with FISO
                    if 'FISO0' in line:
                        line = 'FISO'.join(line.split('FISO0'))

                    # change thermal attack functions
                    line = self.name.join(line.split('FISO'))

                # change convective heat transfer coefficient of steel to 35 in locafi mode according to EN1991-1-2
                elif 'STEEL' in line:
                    init[no + 1] = '{}'.format('35'.join(init[no + 1].split('25')))

            # write changed file
            with open(profile, 'w') as file:
                file.writelines(init)

        def is_in_bounds(beam):
            for n in beam[1:]:
                if self.bounds[0][0] <= n[2] <= self.bounds[0][1] and self.bounds[1][0] <= n[3] <= self.bounds[1][1]:
                    return True

        # add another BEAMTYPE and create corresponding TEM file
        for p in profiles:
            if 'f2a' not in p:
                new_name = f'f2a_{self.name}_{p}'
                profiles.append(new_name)
                modify_tem(new_name) # modify TEM file with proper temperature function
            else:
                break

        # change BEAMTYPE for elements in this layer
        for l, line in enumerate(file_lines[parameters['elemstart']:]):
            elem_data = line.split()
            if 'ELEM' not in line or 'RELAX' in line:
                break
            if is_in_bounds(structure.beams[int(elem_data[1])-1]):
                actual_line = parameters['elemstart'] + l
                for p in profiles:
                    if all([i in p for i in [profiles[int(elem_data[-1])], self.name]]):
                        new_beam_number = profiles.index(p)
                file_lines[actual_line] = f'  \t{"    ".join(elem_data[:-1])}\t{new_beam_number}\n'

        print(f'[OK] Slice {self.name} is ready')


class Slice:
    def __init__(self):
        self.df = pd.DataFrame()
        self.add_all_csvs()

    # from cwd
    def add_all_csvs(self):
       for e in scandir():
           if 'f2a' in e.name:
               self.add_csv2df(e.name)

    def add_csv2df(self, csvfile):
        with open(csvfile) as file:
            data = pd.read_csv(file)
        self.df = pd.concat([self.df, data], axis=1)

    def divide(self, zsize=1, offset=9.4):
        layers = [TempLayer(bounds=[[-1e9, 1e9], [offset + i, offset + i + zsize]]) for i in range(19)]
        for l in layers:
            l.tt_from_df(self.df)
            l.save_function()

        return layers

    def save(self, name):
        self.df.to_csv(abspath(name))


def build_configs():
    iterations = []
    for i in range(0, 1810, 10):
        for j in [55, 67, 76, 82, 83, 91, 97, 103, 109, 115, 121, 127, 133, 134, 139, 140, 145, 146, 153, 154, 159, 160,
                  161, 166, 167, 172, 175, 178, 179, 186, 187, 192, 193, 194, 201, 202, 207, 208, 209, 216, 217, 222,
                  223, 224, 231, 232, 237, 238, 239, 244, 247, 248, 253]:
            iterations.append(FDS2ASCII(chid='hala_urania_safir_s1', filetype=2, samp_fact=1, domain='n',
                                        time=f'{i} {i+10}', variables=[j], out=f'f2a_{i}_{j}.csv'))

    return iterations


if __name__ == '__main__':
    # it = build_configs()
    #
    # for i in it:
    #     i.build_config()
    #     i.save_config()
    #     i.run_f2a()

    # gather slice data and prepare time-temperature files
    s = Slice()
    s.save('slice.csv')
    s.add_all_csvs()
    layers = s.divide()

    # modify structural and create thermal input files
    infile = read_in('hala_urania.in')
    for l in layers:
        l.prepare4safir(infile)
    with open('urania_f2a.in', 'w') as file:
        file.writelines(infile.file_lines)

    # run calculations
    for prof in infile.beamparameters['beamtypes']:
        run_safir(f'{prof}.tem')
    run_safir('urania_f2a.in')
