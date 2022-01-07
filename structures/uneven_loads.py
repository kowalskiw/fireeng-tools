# This script can be used to rename iges files with surfaces to add unven loads that change in the x axis.
# The script helps with creation of input files for area2lineload.py script.
# area2lineload.py is a part of https://github.com/kowalskiw/fireeng-tools.

# This script takes two input arguments:
# 1) txt file with load function where each line is x value and load value separated by space: "x_value load_value\n"
# 2) path to the folder with areas for the area2lineload.py script

# Example load function file:
# -35.4 0
# -17.7 3200
# 0 0
# 17.7 1600
# 35.4 0

import sys
from os.path import basename, dirname, abspath
from os import scandir, makedirs, rmdir, popen
import pyiges
from math import ceil

def getXPositions(path_to_file):
    """Get the lowest and highest x coordinate of the first Rational B-Spline Surface (Type 128) in the iges file"""
    iges_file = pyiges.read(path_to_file)
    bsurfs = iges_file.bspline_surfaces()
    bsurf_points = bsurfs[0].control_points()
    x_min, x_max = bsurf_points[0][0], bsurf_points[0][0]
    for point in bsurf_points:
        if point[0] > x_max:
            x_max = point[0]
        if point[0] < x_min:
            x_min = point[0]
    return x_min, x_max

def calculateLoad(load_function, x_min, x_max):
    """Calculate the load given the load function and start and end values of x"""
    additional_load = 0
    for i in range(len(load_function)-1):
        if x_min > load_function[i][0] and x_min <= load_function[i+1][0]:
            if x_max > load_function[i][0] and x_max <= load_function[i+1][0]:
                x1,    x2    = load_function[i][0], load_function[i+1][0]
                load1, load2 = load_function[i][1], load_function[i+1][1]
                x_avg = (x_min + x_max) / 2
                additional_load = ceil(((x_avg - x1) * (load2 - load1) / (x2 - x1)) + load1)
            elif x_max > load_function[i+1][0]:
                ratio1to2 = (load_function[i+1][0] - x_min)/(x_max - x_min)
                x1,    x2    = load_function[i][0], load_function[i+1][0]
                load1, load2 = load_function[i][1], load_function[i+1][1]
                x = (x_min + load_function[i+1][0]) / 2
                additional_load_1 = ceil(((x - x1) * (load2 - load1) / (x2 - x1)) + load1)
                x1,    x2    = load_function[i+1][0], load_function[i+2][0]
                load1, load2 = load_function[i+1][1], load_function[i+2][1]
                x = (x_max + load_function[i+1][0]) / 2
                additional_load_2 = ceil(((x - x1) * (load2 - load1) / (x2 - x1)) + load1)
                additional_load = ceil(additional_load_1 * ratio1to2 + additional_load_2 * (1 - ratio1to2))
    return additional_load

class UnevenLoads:
    def __init__(self, path_to_areas: str):
        self.paths = {'areas': path_to_areas, 'loaded_areas': '{}\\loaded_areas'.format(dirname(path_to_areas))}
        try:
            rmdir(self.paths['loaded_areas'])
        except FileNotFoundError:
            pass
        except OSError:
            print(f"[ERROR] Catalogue {self.paths['loaded_areas']} already exists and is not empty.")
            print('Delete the files or the whole catalogue and run the script again.')
            exit(1)
        makedirs(self.paths['loaded_areas'])
        self.files = []

    def prepareFilesAndLoads(self, load_function):
        """returns an array containing path and additional load"""
        files = []
        for file in scandir(self.paths['areas']):
            if file.is_file() and any([file.name.lower().endswith(ext) for ext in ['.igs','.iges']]):
                x_min, x_max = getXPositions(file.path)
                additional_load = calculateLoad(load_function, x_min, x_max)
                files.append([file.path, additional_load])
                # print(f"File: {basename(file)}, Position: x_min = {x_min:4.2f}, x_max = {x_max:4.2f} Additional load: {additional_load}")
        self.files = files
    
    def createRenamedFiles(self):
        """Copies renamed files to the loaded_areas folder based on self.files array with path and load"""
        for i in range(len(self.files)):
            #create new basename
            split_basename = basename(self.files[i][0]).split('_')
            basename_loads = split_basename[0].split(' ')
            basename_loads[2] = str(int(basename_loads[2])- self.files[i][1])
            split_basename[0] = ' '.join(basename_loads)
            new_basename = '_'.join(split_basename)

            #copy file with a new name
            source = self.files[i][0]
            destination = f"{self.paths['loaded_areas']}\\{new_basename}"
            popen(f"copy \"{source}\" \"{destination}\"")
            print(f"File: {basename(self.files[i][0])}, Additional load: {self.files[i][1]:4d}, Renamed file: {new_basename}")

if __name__ == '__main__':
    # Import load function from txt file
    load_function = []
    path_to_load_function_txt = abspath(sys.argv[1])
    with open(path_to_load_function_txt, 'r') as load_function_txt:
        for line in load_function_txt.readlines():
            x, load = float(line.split(' ')[0]), float(line.split(' ')[1].strip())
            load_function.append([x, load])
    
    path_to_areas = abspath(sys.argv[2])
    
    case = UnevenLoads(path_to_areas)
    print('[OK] Creation of file paths and additional load calculation started')
    case.prepareFilesAndLoads(load_function)
    print('[OK] Copying renamed files started')
    case.createRenamedFiles()
    print('[OK] Renamed files copied succesfully')
    exit(0)
