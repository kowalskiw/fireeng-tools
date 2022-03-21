from sys import argv
import numpy as np

# args: path to TEM file, critical temperature
# e.g. "python section_temp.py d:\my_sim.gid\hea180.tem 540"


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
    temfile = argv[1]
    temp_crit = float(argv[2])

    [print_data(data[1], data[0]) for data in [('min temperature', min_temp(temfile)),
                                               ('mean temperature', mean_temp(temfile)),
                                               ('max temperature', max_temp(temfile))]]
