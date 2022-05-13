from os import scandir, mkdir
from shutil import copy2 as cp
from sys import argv

if len(argv) > 1:
    config_dir = argv[1]
else:
    config_dir = '.'

extension = input('give me extension: ')

ins_path = '{}\{}s'.format(config_dir, extension)
try:
    mkdir(ins_path)
except FileExistsError:
    ins_path += '1'
    mkdir(ins_path)

for d in scandir():
    if '.gid' in d.name:
        in_path = '{}\{}\{}.{}'.format(config_dir, d.name, d.name.split('.gid')[0], extension)
        cp(in_path, ins_path)
