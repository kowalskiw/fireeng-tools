import subprocess
import sys
from os import getcwd, chdir
from datetime import datetime as dt

from xml.dom.minidom import parse as pxml
from xml.etree import ElementTree
from os.path import dirname, basename, abspath, exists


def repair_relax_in_xml(xml_file_path):
    """Modifies relaxations in the XML output file to the correct format for Diamond"""
    # Check if there is </SAFIR_RESULTS> at the end of the file

    # Currently works only for beams
    print(f"[WAIT] Parsing the {basename(xml_file_path)} file")
    tree = ElementTree.parse(xml_file_path)
    print(f"[OK] File parsed")

    def modify_rlx(rlx_text):
        return rlx_text.replace('-0.100E+01', '-1').replace('0.000E+00', '0')

    for rlx in tree.find('RELAX/BEAMS'):
        rlx.text = modify_rlx(rlx.text)
    print("[OK] Relaxations modified")

    print(f"[WAIT] Writing changes to the {basename(xml_file_path)} file")
    tree.write(xml_file_path)
    print(f"[OK] Changes written to the {basename(xml_file_path)} file")


# running SAFIR simulation
def run_safir(in_file_path, safir_exe_path='C:\SAFIR\safir.exe', print_time=True, fix_rlx=True, verbose=False):
    start = dt.now()
    print(f'[INFO] Calculations started at {start}') if print_time else None
    backpath = getcwd()
    dirpath = dirname(in_file_path)
    chdir(dirpath)
    chid = basename(in_file_path)[:-3]

    print(f'Reading {chid}.in file...')
    process = subprocess.Popen(' '.join([safir_exe_path, chid]), shell=False, stdout=subprocess.PIPE)
    print_all = verbose
    success = True
    count = 0

    # clear output
    while True:
        if process.poll() is not None:
            break
        try:
            output = process.stdout.readline().strip().decode()
        except UnicodeError:
            continue
        if output:
            if print_all:
                print('    ', output)
            # check for errors
            elif 'ERROR' in output or 'forrtl' in output:
                print('[ERROR] FatalSafirError: ')
                print_all = True
                success = False
                print('    ', output)
            elif '======================' in output:
                count += 1
            # check for timestep
            elif 'time' in output and print_time:
                print(f'SAFIR started "{chid}" (sim #{count}) calculations: {output[7:]}', end='\r')

    rc = process.poll()
    chdir(backpath)

    if not rc:
        if success:
            print(f'[OK] SAFIR finished {count} "{chid}" calculations at')
            print(f'[INFO] Computing time: {dt.now() - start}')
            repair_relax(f'{dirpath}\\{chid}.XML') if fix_rlx else None
            return 0
        else:
            print(f'[WARNING] SAFIR finished "{chid}" calculations with error!')
            return -1


def repair_relax(path_to_xml, copyxml=True):
    rlx_lines = []
    index = 0
    fixed = 0

    with open(path_to_xml) as xmlfile:
        for line in xmlfile:
            if 'RLX' in line:
                rlx_lines.append('0'.join('-1'.join(line.split('-0.100E+01')).split('0.000E+00')))
                fixed += 1
            else:
                rlx_lines.append(line)

            index += 1

    with open(f'{path_to_xml[:-4]}_fixed.XML' if copyxml else path_to_xml, 'w') as newxml:
        newxml.writelines(rlx_lines)

    print(f'[OK] {fixed} XML file lines fixed (relaxations bug)')

    return 0


# call functions to read single parts of results file
class ReadXML:
    def __init__(self, pathtoresults):
        self.doc = pxml(pathtoresults)

    def reactions(self, timestep):
        reactions = []
        temp = []
        nr = -1

        for node in self.doc.getElementsByTagName('REACTIONS')[timestep].childNodes[1:-1:2]:
            if node.nodeName == 'N':
                temp = []
                x = int(node.firstChild.data)
                temp.append(int(x))
            elif node.nodeName == 'NR':
                nr = int(node.firstChild.data)
            elif node.nodeName == 'R':
                x = float(node.firstChild.data)
                temp.append(x)

            reactions.append(temp) if len(temp) == nr else None

        return reactions

    def mnvs(self, timestep):
        mnvs = []
        bmvalues = []
        temp = []
        ngb = int(self.doc.getElementsByTagName('NGBM')[0].firstChild.data)

        for bm in self.doc.getElementsByTagName('MNV')[1+timestep].childNodes:
            for gs in bm.childNodes:
                for i in gs.childNodes:
                    try:
                        temp.append(float(i.firstChild.data))
                    except AttributeError:
                        pass

                if len(temp) == 7:
                    bmvalues.append(temp)
                    temp = []
            if len(bmvalues) == ngb:
                mnvs.append(bmvalues)
                bmvalues = []

        return mnvs

    def nodes(self):
        nodes = []
        point = []
        for node in self.doc.getElementsByTagName('NODES')[0].childNodes[1:-1:2]:
            if node.nodeName == 'N':
                point = []
                for p in node.childNodes[1:-1:2]:
                    point.append(p.firstChild.data)

            nodes.append([float(coord) for coord in point]) if len(point) == 3 else None

        return nodes

    def beams(self):
        print('ReadXML.beams() module not ready yet')
        pass


# load all results file to Python DB
class LoadFullXML(ReadXML):
    def __init__(self, pathtoresults):
        super().__init__(pathtoresults)
        # read all data
    pass


def read_in(path):
    with open(path) as file:
        f = file.readlines()

    # in the future add recognizing of analysis type
    # type = s3d/t2d/tsh2d/t3d/s2d

    return InFile(basename(path)[:-3], f, type=None)


class InFile:
    def __init__(self, chid, file_lines, type=None):
        self.file_lines = file_lines
        self.chid = chid
        self.type = 'type_of_analysis'
        self.nodes = self.get(0)
        self.beams = self.get(1)
        self.shells = self.get(2)
        self.solids = self.get(3)
        self.beamparameters = self.get_beamparameters()

        self.t_end = self.get_time()

    # import entities
    def get(self, entity_type):
        got = []
        keys = []   # [start, element, end (tuple if many options possible)]

        if entity_type in ['node', 'nodes', 'n', 0]:
            keys = ['NODES', 'NODE', ['FIXATIONS']]
            entity_type = 0
        elif entity_type in ['beam', 'beams', 'b', 1]:
            keys = ['NODOFBEAM', 'ELEM', ['NODOFSHELL', 'NODOFSOLID', 'PRECISION', 'RELAX_ELEM']]
            entity_type = 1
        elif entity_type in ['shell', 'shells', 'sh', 2]:
            keys = ['NODOFSHELL', 'ELEM', ['NODOFBEAM', 'NODOFSOLID', 'PRECISION', 'RELAX_ELEM']]
            entity_type = 2
        elif entity_type in ['solid', 'solids', 'sd', 3]:
            keys = ['NODOFSOLID', 'ELEM', ['NODOFBEAM', 'NODOFSHELL', 'PRECISION', 'RELAX_ELEM']]
            entity_type = 3

        read = False
        for line in self.file_lines:
            if keys[0] in line:
                read = True
            elif read and any(stop in line for stop in keys[2]):
                break
            elif read and keys[1] in line:
                lsplt = line.split()
                if entity_type == 0:
                    got.append([float(i) for i in lsplt[2:]])  # coordinates
                    got[-1].insert(0, int(lsplt[1]))    # entity tag
                else:
                    got.append([int(i) for i in lsplt[1:]])  # entity tag and lower entities tags

        return got

    def get_time(self):
        for i, l in enumerate(reversed(self.file_lines)):
            if 'ENDTIME' in l:
                return float(self.file_lines[-i-2].split()[1])

    def get_beamparameters(self):
        beamparameters = {}
        lines = 0
        
        beamparameters['index'] = [x for x in range(len(self.file_lines)) if 'NODOFBEAM' in self.file_lines[x]][0] #where NODOFBEAM appears - beamparameters in inFile.file_lines starts
        beamparameters['beamtypes']= []
        

        beamparameters['beamline'] = [x for x in range(len(self.file_lines)) if 'BEAM' in self.file_lines[x]][0]  #where beam line appears (begining of the file)
        beamparameters['elemstart']= 0

        for line in self.file_lines[beamparameters['index']+1:]:#how many lines till ELEM appears- beams ends (every beam has 3 lines)
            if "ELEM" not in line:
                if line.endswith(".tem\n"):
                    beamparameters['beamtypes'].append(line[:-5]) 
                if line.endswith(".tem"):
                    beamparameters['beamtypes'].append(line[:-4]) # question? - are here possibilities to have line ending without \n ?   
                lines+=1
            else:
                beamparameters['elemstart'] = beamparameters['index']+2+lines

        beamparameters['beamnumber'] = len(beamparameters['beamtypes'])
        return beamparameters


# if you want to run a function from this file, add the function name as the first parameter
# the rest of the parameters will be forwarded to the called function (files as a full path)
if __name__ == '__main__':
    try:
        function = sys.argv[1]

        # change to full path if it is a file name
        args = []
        for arg in sys.argv[2:]:
            args.append(abspath(arg) if exists(abspath(arg)) else arg)

        globals()[function](*args)
        exit(0)
    except IndexError:
        raise Exception("Please provide function name")
    except KeyError:
        raise Exception(f"Function {function} was not found")
