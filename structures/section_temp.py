from sys import argv
import argparse
import numpy as np
import xml.etree.ElementTree as ET


# args: use -h flag to get some help
# e.g. "python section_temp.py -f d:\my_sim.gid\hea180.tem -c 540 -x"

class ReadXML:
    def __init__(self, path2xml, amb_temp=20):
        self.data = ET.parse(path2xml).getroot()
        self.ambient = amb_temp
        self.steel_nmat = []
        self.temperatures = {}
        self.check_if_t2d(path2xml.split('/')[-1])

    def check_if_t2d(self, name):
        for n in self.data.iter('NDIM'):
            if '2' in n.text:
                break
            else :
                raise TypeError(f'{name} does not contain 2D results. Give me the right file, man!')

        for t in self.data.iter('TYPE'):
            if 'TEMPERAT' in t.text:
                break
            else :
                raise TypeError(f'{name} does not contain thermal results. Give me the right file, man!')

        for m in self.data.iter('MATERIALS'):
            for i, v in enumerate(m):
                if 'STEEL' in v.text:
                   self.steel_nmat.append(i+1)
            if len(self.steel_nmat) == 0:
                raise TypeError(f'{name} does not contain steel nodes. Give me the right file, man!')
            
        print(f'[OK] {name} file loaded')

    def find_steel_nodes(self):
        for n in self.data.iter('NNODE'):
            nnodes = int(n.text)

        self.steel_nodes = list(range(1, nnodes))
        
        for solids in self.data.iter('SOLIDS'):
            for i, s in enumerate(solids):
                if int(s[-1].text) not in self.steel_nmat:
                    for n in s[:-1]:
                        try :
                            self.steel_nodes.remove(int(n.text))
                        except ValueError:
                            continue

        print(f'[OK] {len(self.steel_nodes)} steel nodes out of total {nnodes} were taken')

    def find_times(self):
        times = []
        for time in self.data.iter('TIME'):
            times.append(float(time.text))

        return times


    def load_temps(self):
        self.find_steel_nodes()
        times = self.find_times()

        for i, t in enumerate(self.data.iter('TEMPERATURES')):
            step = []
            for n in self.steel_nodes:
                step.append(float(t[n-1].text))
            self.temperatures[times[i]] = step
        
        return self.temperatures
    



class Statistics:
    def __init__(self, temp_data, nodes=None):
        self.data = temp_data   # {timestep[s]: [temp_node1, ... temp_nodeN], ...}
        self.nodes = nodes  # None if aritmetic: a_1 = 1 and a_{n+1} = a_n + 1

    def _stat_return(self, function, xy, prnt=True, plot=False):
        # calculate stat
        tab = {}
        for time, vals in self.data.items():
            tab[time] = function(vals)

        # print 
        if prnt:
            print_data2(tab)

        # plot
        if plot:
            # include plotting methods
            pass

        # return
        if xy:
            xes = []
            yes = []
            for x, y in tab.items():
                xes.append(x)
                yes.append(y)
            return xes, yes
        else :
            return tab


    def mean(self, xy=False):
        print('[INFO] Mean temperatures')
        lmean = lambda x: round(np.mean(x), 2)

        return self._stat_return(lmean, xy)

    def min(self, xy=False):
        print('[INFO] Minimum temperatures')
        lmin = lambda x: min(x)

        return self._stat_return(lmin, xy)

    def max(self, xy=False):
        print('[INFO] Maximum temperatures')
        lmax = lambda x: max(x)

        return self._stat_return(lmax, xy)

    def all_stats(self):
        stats = {}
        stats['min'] = self.min()
        stats['mean'] = self.mean()
        stats['max'] = self.max()

        return stats
    
    def plot_all(self):
        pass

    def print_all(self):
        pass

    

def print_data2(ddict):
    times = list(ddict)
    temps = list(ddict.values())

    print('_____________________________')
    print('Time, [s] | Temperature, [°C]')
    print('----------|------------------')
    for time, temp in ddict.items():
        print(time, ' '*(8-len(str(time))), '|', temp)
    print('-----------------------------')

    print(f'Max temperature in the table: {round(max(temps), 1)}')

    if max(temps) > temp_crit:
        crittime = round(np.interp(temp_crit, temps, times))

        print(f'Critical temperature in the table was exceeded at {crittime} s (interpolated)')
    else:
        print('Critical temperature has not been reached in the table')
    print('==============================================================')



### OBSOLETE ###
def mean_temp(temfile_path, amb_temp=20):
    nfiber = 0
    is_reading_temp = False
    temperature = 0
    t = 0
    section_temp = []

    with open(temfile_path) as file:
        tem = file.readlines()

    for line in tem:
        # set number of elements
        if 'NFIBERBEAM' in line:
            nfiber = int(line.split()[1])

        # set time step value and reset temperature
        elif 'TIME' in line:
            temperature = 0
            t = float(line.split()[1])
            is_reading_temp = True

        # try to save previous step mean cross-section temperature
        elif line.startswith('\n'):
            try:
                section_temp.append([t, temperature / nfiber])
                is_reading_temp = False
            except UnboundLocalError:
                is_reading_temp = False

        # add temperature in element in certain step
        elif is_reading_temp:
            try:
                fiber_temp = float(line.split()[-1])
                if fiber_temp >= amb_temp:
                    temperature += fiber_temp
                else:
                    print('[WARNING] SafirError: Fiber temperature is lower than ambient ({} °C < {} °C)'.format(
                        fiber_temp, amb_temp))
                    raise ChildProcessError
            except (IndexError, UnboundLocalError, ValueError):
                pass

    return np.array(section_temp[1:])


def max_temp(temfile_path, amb_temp=20):
    is_reading_temp = False
    temperature = 0
    t = 0
    section_temp = []

    with open(temfile_path) as file:
        tem = file.readlines()

    for line in tem:
        # set time step value and reset temperature
        if 'TIME' in line:
            temperature = 0
            t = float(line.split()[1])
            is_reading_temp = True

        # try to save previous step mean cross-section temperature
        elif line.startswith('\n'):
            try:
                section_temp.append([t, temperature])
                is_reading_temp = False
            except UnboundLocalError:
                is_reading_temp = False

        # check if temperature is higher in certain step
        elif is_reading_temp:
            try:
                fiber_temp = float(line.split()[-1])
                if fiber_temp >= amb_temp:
                    if fiber_temp > temperature:
                        temperature = fiber_temp
                else:
                    print('[WARNING] SafirError: Fiber temperature is lower than ambient ({} °C < {} °C)'.format(
                        fiber_temp, amb_temp))
                    raise ChildProcessError
            except (IndexError, UnboundLocalError, ValueError):
                pass

    return np.array(section_temp[1:])


def min_temp(temfile_path, amb_temp=20):
    is_reading_temp = False
    temperature = 999999
    t = 0
    section_temp = []

    with open(temfile_path) as file:
        tem = file.readlines()

    for line in tem:
        # set time step value and reset temperature
        if 'TIME' in line:
            temperature = 99999
            t = float(line.split()[1])
            is_reading_temp = True

        # try to save previous step mean cross-section temperature
        elif line.startswith('\n'):
            try:
                section_temp.append([t, temperature])
                is_reading_temp = False
            except UnboundLocalError:
                is_reading_temp = False

        # check if temperature is lower in certain step
        elif is_reading_temp:
            try:
                fiber_temp = float(line.split()[-1])
                if fiber_temp >= amb_temp:
                    if fiber_temp < temperature:
                        temperature = fiber_temp
                else:
                    print('[WARNING] SafirError: Fiber temperature is lower than ambient ({} °C < {} °C)'.format(
                        fiber_temp, amb_temp))
                    raise ChildProcessError
            except (IndexError, UnboundLocalError, ValueError):
                pass

    return np.array(section_temp[1:])


def print_data(temp_array, title):
    time, temp = zip(*temp_array)
    temp_max = round(max(temp), 1)

    print(f'\n\n{title.upper()} TABLE')
    print('_____________________________')
    print('Time, [s] | Temperature, [°C]')
    print('----------|------------------')
    for i in temp_array:
        print(int(i[0]), ' '*(10-len(str(i[0]))), '|', round(i[1], 2))

    print(f'\nMaximum temperature in the table: {temp_max}')

    if max(temp) > temp_crit:
        crittime = -999
        for r in temp_array:
            if r[1] >= temp_crit:
                crittime = r[0]
                break
        print(f'\nExceeding critical temperature time: {crittime} s')
    else:
        print('\nCritical temperature has not been reached\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Section temperatures from SAFIR by kowalskiw')
    parser.add_argument('-x', '--xml', help='Read results from XML file', default=True, action='store_true')
    parser.add_argument('-t', '--tem', help='Read results from TEM file (obsolete)', default=False, action='store_true')
    parser.add_argument('-f', '--file', help='Path to results file', required=True)
    parser.add_argument('-c', '--critical',type=float, help='Critical temperature [°C]', required=True)

    args = parser.parse_args()

    temp_crit = args.critical

    if args.xml and args.tem:
        raise TypeError('Specify only one mode (-x OR -t). Use -h for help.')
    elif args.xml:
        rx = ReadXML(args.file)
        s = Statistics(rx.load_temps())
        s.all_stats()
    elif args.tem:
        [print_data(data[1], data[0]) for data in [('min temperature', min_temp(args.file)),
                                                   ('mean temperature', mean_temp(args.file)),
                                                   ('max temperature', max_temp(args.file))]]


