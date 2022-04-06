from os import scandir, chdir
from os.path import abspath
from subprocess import run

import numpy as np
import pandas as pd

from safir_tools import read_in, run_safir


class FDS2ASCII:
    def __init__(self, chid='', filetype=0, samp_fact=0, domain='', bounds='', time='', orient=0, variables=None,
                 inp='input.txt', out=''):
        if variables is None:
            variables = [1]
        self.chid = chid  # Enter Job ID string (CHID)
        self.filetype = filetype  # What type of file to parse? | PL3D file? Enter 1 | SLCF file? Enter 2 | BNDF file? Enter 3
        self.samp_factor = samp_fact  # Enter Sampling Factor for Data? (1 for all data, 2 for every other point, etc.)
        self.domain = domain  # Limit the domain size? (y or n)
        self.bounds = bounds  # Enter min/max x, y and z
        self.time = time  # Enter starting and ending time for averaging (s)
        self.orientation = orient  # Enter orientation: (plus or minus 1, 2 or 3)
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
        run(f'fds2ascii < {self.input}', shell=True)


class TempLayer:
    def __init__(self, bounds=None):
        if bounds is None:
            bounds = [[0, 0], [0, 0], [0, 0]]
        self.bounds = bounds
        self.temp_time = [[0, 20]]
        self.name = f'f_{int(self.bounds[2][0] * 10)}-{int(self.bounds[2][1] * 10)}'
        self.layer_df = pd.DataFrame()
        self.temp_time_dict = {}

    def add_data(self, data):
        self.layer_df = pd.concat([self.layer_df, data[(self.bounds[0][0] <= data['C1']) &
                                                       (data['C1'] <= self.bounds[0][1]) &
                                                       (self.bounds[2][0] <= data['C2']) &
                                                       (data['C2'] <= self.bounds[2][1])]])

        return self.layer_df

    def add_mean_data(self, data):
        df = data[(self.bounds[0][0] <= data['C1']) & (data['C1'] <= self.bounds[0][1]) &
                  (self.bounds[2][0] <= data['C2']) & (data['C2'] <= self.bounds[2][1])]

        timestep = df.keys()[-1]
        interior = df[timestep][(df[timestep] > 20.5)]
        mean = interior.mean()
        weight = len(interior.index)
        if weight:
            try:
                self.temp_time_dict[str(timestep)].append([mean, weight])
            except KeyError:
                self.temp_time_dict[str(timestep)] = [[mean, weight]]

    def tt_from_df(self):
        for i, t in self.layer_df.iloc[2:, 1:].iteritems():
            timestep = []
            for j, cell in t.iterrows():
                if cell > 20.5:
                    timestep.append(t)
            try:
                self.temp_time.append([i, sum(timestep) / len(timestep)])
            except ZeroDivisionError:
                self.temp_time.append([i, 20])

        return self.temp_time

    def tt_from_dict(self):
        for k, v in self.temp_time_dict.items():
            av_val = 0
            av_weight = 0
            for i in v:
                av_val = av_val + i[0] * i[1]
                av_weight += i[1]
            if av_val == 0 and av_weight == 0:
                av_val = 20
                av_weight = 1
            self.temp_time.append([int(k), av_val / av_weight])

        return self.temp_time

    def save_function(self, name=None):
        self.temp_time.sort(key=lambda x: x[0])

        n = self.name if not name else name
        with open(n, 'w') as file:
            file.writelines([f'{i[0]}\t{i[1]}\n' for i in self.temp_time])

    def prepare4safir(self, structure):
        parameters = structure.beamparameters
        profiles = parameters['beamtypes']

        def modify_in(old, profile):
            with open(f'{old}.in') as file:
                init = file.readlines()

            # make changes
            for no, line in enumerate(init):
                # change thermal attack functions
                if line.startswith('   F  ') and 'FISO' in line:  # choose heating boundaries with FISO or FISO0 front
                    # replace FISO0 with FISO
                    if 'FISO0' in line:
                        line = 'FISO'.join(line.split('FISO0'))

                    # change thermal attack functions
                    init[no] = self.name.join(line.split('FISO'))

                # change convective heat transfer coefficient of steel to 35 in locafi mode according to EN1991-1-2
                elif 'STEEL' in line:
                    init[no + 1] = '{}'.format('35'.join(init[no+1].split('25')))

            # write changed file
            with open(f'{profile}.in', 'w') as file:
                file.writelines(init)

        # check if beam is in bounds of the layer (self.bounds)
        def is_in_bounds(beam, nodes):
            if all([all([self.bounds[i][0] <= nodes[n-1][i+1] <= self.bounds[i][1] for i in range(3)]) for n in beam[1:]]):
                return True

        # add another BEAMTYPE and create corresponding TEM file
        for p in profiles:
            if 'f2a' not in p:
                new_name = f'f2a_{self.name}_{p}'
                profiles.append(new_name)
                modify_in(p, new_name)  # modify TEM file with proper temperature function
            else:
                break

        # change BEAMTYPE for elements in this layer
        for l, line in enumerate(structure.file_lines[parameters['elemstart']:]):     # parse over all BEAM elements
            elem_data = line.split()
            if 'ELEM' not in line or 'RELAX' in line:   # break condition
                break
            if is_in_bounds(structure.beams[int(elem_data[1]) - 1], structure.nodes):   # check if the BEAM is in the layer
                actual_line = parameters['elemstart'] + l
                for p in profiles:
                    if all([i in p for i in [profiles[int(elem_data[-1])], self.name]]):
                        new_beam_number = profiles.index(p)
                try:
                    structure.file_lines[actual_line] = f'  \t{"    ".join(elem_data[:-1])}\t{new_beam_number}\n'
                except UnboundLocalError:
                    print(l, line)
                    # print(structure.nodes[int(elem_data[2])])
                    # print(actual_line)
                    # print(int(elem_data[-1]), np.array(profiles), self.name)
                    exit()

        print(f'[OK] Slice {self.name} is ready')

        return structure


class Slice:
    def __init__(self):
        self.df = pd.DataFrame()

    # from cwd
    def add_all_csvs(self):
        i = 0
        for e in scandir():
            if 'f2a' in e.name:
                self.add_csv2df(e.name)
                i += 1
                print(f'{i}/{43 * 181} ({i / 43 / 1.81}%) CSV files added {e.name}\r')

    def add_csv2df(self, csvfile):
        with open(csvfile) as file:
            data = pd.read_csv(file, low_memory=False)
        self.df = pd.concat([self.df, data], axis=0)

    # def divide(self, zsize=1, offset=9.4):
    #     layers = [TempLayer(bounds=[[-1e9, 1e9], [-1e9, 1e9], [offset + i, offset + i + zsize]]) for i in range(19)]
    #     print('[OK] Layers created')
    #     for i, l in enumerate(layers):
    #         print(f'{i}/{len(layers)} ({i/len(layers)*100}%)')
    #         l.tt_from_df(self.df)
    #         l.save_function()
    #
    #     return layers

    def save(self, name):
        self.df.to_csv(abspath(name))


def build_configs():
    iterations = []
    for i in range(1780, 1810, 10):
        for j in [55, 67, 76, 82, 83, 91, 97, 103, 109, 115, 121, 127, 133, 134, 139, 140, 145, 146, 154, 160, 161, 166,
                  167, 172, 175, 178, 179, 187, 193, 194, 202, 208, 209, 217, 223, 224, 232, 238, 239, 244, 247, 248,
                  253]:
            iterations.append(FDS2ASCII(chid='hala_urania_safir_s1', filetype=2, samp_fact=1, domain='n',
                                        time=f'{i} {i + 10}', variables=[j], out=f'f2a_{i}_{j}.csv'))

    return iterations


def extract_data():
    for i in build_configs():
        i.build_config()
        i.save_config()
        i.run_f2a()


def do_layers(zsize=1, offset=9.4):
    layers = [TempLayer(bounds=[[-1e9, 1e9], [-1e9, 1e9], [offset + i, offset + i + zsize]]) for i in range(19)]

    # print('[OK] Layers created')
    # for i, l in enumerate(layers):
    #     print(f'{i}/{len(layers)} ({i/len(layers)*100}%)')
    #     l.tt_from_df(df)
    #     l.save_function()

    return layers


if __name__ == '__main__':
    # extract_data()
    chdir('fds2ascii')
    layers = do_layers()

    i = 0
    for e in scandir():
        if 'f2a' in e.name:
            with open(e.name) as file:
                df = pd.read_csv(file, names=['C1', 'C2', f'{e.name.split("_")[1]}'], skiprows=[0, 1], dtype=float)
            for l in layers:
                l.add_mean_data(df)
            i += 1
            print(f'{i}/{43 * 180} ({round(i / 43 / 1.8, 2)}%) CSV files scanned {e.name}\r')

    chdir('..')

    # # gather slice data and prepare time-temperature files
    # s.save('slice1.csv')
    # exit(0)
    # s.add_csv2df('slice.csv')
    # print('Slice added')
    # print(s.df.head())
    # layers = s.divide()

    # modify structural and create thermal input files
    infile = read_in('hala_urania.in')
    for l in layers:
        l.tt_from_dict()
        l.save_function()
        infile = l.prepare4safir(infile)
    with open('urania_f2a.in', 'w') as file:
        file.writelines(infile.file_lines)

    # run calculations
    print(infile.beamparameters['beamtypes'])
    for prof in infile.beamparameters['beamtypes']:
        run_safir(abspath(f'{prof}.in'))
    run_safir('urania_f2a.in')
