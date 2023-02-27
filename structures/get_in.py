from os import scandir, mkdir
from shutil import copy2 as cp
from sys import argv
from os.path import abspath, exists
from datetime import datetime


def get_dirs_and_extensions_from_args():
    """
    Creates a working directory path to copy the files from (1st cmd argument) and a list of file extensions to copy (the rest of the arguments).
    Path to working directory is optional, default value: '.'. Default file extension: in.
    Output: string (path to working directory), list of strings (file extensions to copy)
    """
    if len(argv) > 1:
        extensions = []
        if exists(abspath(argv[1])):
            working_directory_path = abspath(argv[1]) 
        else: 
            working_directory_path = '.'
            extensions.append(argv[1])
        for arg in argv[2:]:
            extensions.append(arg)
    else:
        working_directory_path = '.'
        extensions = ["in"]
    return working_directory_path, extensions

def make_config_directory(working_directory_path, config_directory_name):
    config_directory_path = f"{working_directory_path}\{config_directory_name}"
    try:
        mkdir(config_directory_path)
    except FileExistsError:
        now_string = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_directory_path += f'_{now_string}'
        mkdir(config_directory_path)
    return config_directory_path

def copy_files(working_directory_path, config_directory, extensions):
    """
    Copy files with given extensions from folders in working_directory_path with .gid in the name to config_directory.
    """
    for directory in scandir(working_directory_path):
        for extension in extensions:
            if '.gid' in directory.name:
                in_path = f"{working_directory_path}\{directory.name}\{directory.name.split('.gid')[0]}.{extension}"
                if extension == "T0R":
                    in_path = f"{working_directory_path}\{directory.name}\{directory.name.split('.gid')[0]}-1.{extension}"
                cp(in_path, config_directory)

def main():
    working_directory_path, extensions = get_dirs_and_extensions_from_args()

    config_directory_path = make_config_directory(working_directory_path, "_config")
    print(f"{config_directory_path=}")
    
    copy_files(working_directory_path, config_directory_path, extensions)

if __name__ == '__main__':
    main()