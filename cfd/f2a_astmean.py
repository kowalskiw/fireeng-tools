from os import chdir
from subprocess import Popen, PIPE
from sys import argv
from pandas import read_csv as rcsv
import pandas


class F2A:
    def __init__(self, time, orientation, sample_size=1):
        self.time = time
        self.orientation = orientation
        self.ssize = sample_size
        chdir(argv[1])

    # read() generates CSV files for each side and time sample
    # bounds parameter is XB type coordinates of space (OBST in fact) taken into account while reading data from
    #                   fds output
    # mesh parameter stands for number of mesh that consists bounds space
    # ssize is time sample size in seconds, for steel member analysis 1s is recommended
    def read(self, bounds, mesh):
        chid = argv[2]

        proc = Popen('cmd.exe', stdin=PIPE)
        for t in range(self.time[0], self.time[1], self.ssize):
            for o in self.orientation:
                sas = 'f2a_{}_{}.csv'.format(t, o)
                c = ['fds2ascii', chid, '3', '1', 'y', bounds, '{} {}'.format(t, t + 10), o, '1', mesh, sas]
                [proc.stdin.write(bytes('{}\n'.format(com), encoding='utf8')) for com in c]
                print(sas)

    # split_ast() allows to gather data according to time grouped by cells -- f(t) tables
    # 0) create pandas df (id - time, columns - cells)
    # 1) select proper patch (set in FDS only one OBST as BNDF=T, there would be only one patch in each direction)
    # 2) remove headers
    # 3) add data as next row in df
    # 4) save df as CSV file
    def split_ast(self):
        df = pandas.DataFrame()
        for t in range(self.time[0], self.time[1], self.ssize):
            for o in self.orientation:
                name = 'f2a_{}_{}.csv'.format(t, o)

                # need to be more versatile
                if len(df.index) == 0:
                    cells = []
                    with open(name) as file:
                        print()
                        for line in file.readlines()[3:]:
                            cells.append(''.join(line.split(',')[:3]))
                    df = pandas.DataFrame(columns=['time', *cells])

                print(len(df.columns))
                print(len([t] + self.row_maker(name)))
                df.loc[t/self.ssize] = [t] + self.row_maker(name)

        with open('value.csv', 'w') as file:
            file.write(df.to_csv())

    def row_maker(self, name):
        # change CSV file to applicable form

        with open(name) as file:
            lines = file.readlines()
        if lines[0][:5] == 'Patch':
            lines.pop(0)
            lines.pop(1)
            for i in range(len(lines[1:])):
                lines[i+1] = ','.join([str(i), lines[i+1]])
            with open(name, 'w') as file:
                file.writelines(lines)

        csv = rcsv(name)
        row = []
        csv.columns = csv.columns.str.strip().str.replace(' ', '_')

        for v in csv.iloc[:, -1]:
            if type(v) != str():
                row.append(v)

        return row

    # split_mean() takes data from CSV files generated with fds2ascii into one DB ready for calculating mean values
    def split_mean(self, file):
        data = {}
        with open('temp.csv', 'w') as temp:
            temp.write(file)
        with open('temp.csv', 'r') as temp:
            f = temp.readlines()
        patch_no = f[0].split(' ')[0]
        with open('temp.csv', 'w') as temp:
            temp.writelines(f[1:])

        file = rcsv('temp.csv')
        file.drop(0, inplace=True)
        print(file.columns)

        # split according to Z

        file.drop([' X', 'Z'], axis='columns', inplace=True)

        # save in data dictionary as title:array(pandas df)
        # title = 'Patch{} X={} Z={}'.format(patch_no, x, z)
        # data{title:array}

        return data

    # DorA
    # mean() allows to calculate mean temperature of given cross-section
    def mean(self):
        data_list = []

        for t in range(self.time[0], self.time[1], 10):
            for o in self.orientation:
                # split csv files for specified bounds
                with open('f2a_{}_{}.csv'.format(t, o))as temp:
                    files = temp.read().split('Patch ')
                [self.split_csv(f) for f in files[1:]]
                # merge splitted csv files using Y as key

                data_list.append(rcsv('f2a_{}_{}.csv'.format(t, o), sep=','))
                break
            break
        # count mean value of each cross section (Y)

        # add to the time array

        # draw temp(time) chart for given cross-section
        # draw temp(Y) chart for given time

        # enjoy your data!


f2a = F2A([0, 10], [-1, 1], sample_size=10)
f2a.split_ast()
# readX([0, 600], [-1, 1], '3 4 25 35 6 8', 8)
