import os.path
import subprocess
import sys
from os import getcwd, chdir, symlink
from datetime import datetime as dt

from xml.dom.minidom import parse as pxml
from xml.etree import ElementTree
from os.path import dirname, basename, abspath, exists

from file_read_backwards import FileReadBackwards as frb



### USEFUL FUNCTIONS TO BE USED WITH SAFIR ###

def repair_relax_in_xml(xml_file_path):
    """Modifying relaxations in the XML output file to the correct format for Diamond"""
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


def run_safir(in_file_path, safir_exe_path='safir', print_time=True, fix_rlx=True, verbose=False, wine=False, key=None):
    '''Running SAFIR simulation with clear output under Linux or Windows'''
    start = dt.now()
    backpath = getcwd()
    dirpath = dirname(in_file_path)
    chdir(dirpath)
    chid = basename(in_file_path)[:-3]
    
    if key:
        try:
            symlink(key, './identity.key')
            print('[OK] License file linked')
        except FileExistsError:
            print('[OK] License file already linked')

    print(f'[INFO] Calculations started at {start}') if print_time else print(f'Running {chid}...')
    print(f'Reading {chid} input file...') if print_time else None
    if not wine:
        process = subprocess.Popen([safir_exe_path, chid], shell=False, stdout=subprocess.PIPE)
    else:
        process = subprocess.Popen(['wine', safir_exe_path, chid], shell=False, stdout=subprocess.PIPE)

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
            if print_time:
                count = 1 if count == 0 else count
                print(f'[OK] SAFIR finished {count} "{chid}" calculations at')
                print(f'[INFO] Computing time: {dt.now() - start}')
            repair_relax(f'{dirpath}/{chid}.XML') if fix_rlx else None
            return 0
        else:
            print(f'[WARNING] SAFIR finished "{chid}" calculations with error!')
            return -1


def repair_relax(path_to_xml, copyxml=True, verb=True):
    '''Modifying relaxations in the XML output file to the correct format for Diamond --- no xml packages'''
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

    print(f'[OK] {fixed} XML file lines fixed (relaxations bug)') if verb else None

    return 0


def move_in(infile_path, x, y, z):
    '''Moving the model with given vector'''
    infile = read_in(infile_path)
    infile.move([float(i) for i in [x, y, z]])
    infile.save_line(f'{infile.chid}_moved.in')
    print(f'[OK] Model moved with ({x}, {y}, {z}) vector')


def preview(xmlfile_path):
    '''Preview of XML results while calculation process is not finished yet'''

    temp_xml_lines = ['</SAFIR_RESULTS>\n']
    last_step = 0
    do_write = False

    i = 0
    with frb(xmlfile_path, encoding='utf-8') as backward:
        for l in backward:
            print(f'Reading line {i} of original XML file...', end='\r')
            if 'RLX' in l:  #prevent relaxations bug
                temp_xml_lines.insert(0, '0'.join('-1'.join(line.split('-0.100E+01')).split('0.000E+00')))
            if do_write:
                temp_xml_lines.insert(0, l+'\n')
                if 'TIME' in l and last_step == 0:
                    #<TIME format="F14.5">      13.00000</TIME>
                    last_step = float(l[21:-7])

            elif 'STEP' in l:
                do_write = True
            i+=1

    with open(f'{xmlfile_path[:-4]}_{last_step}.xml', 'w') as newxml:
        print(f'Saving {xmlfile_path[:-4]}_{last_step}.xml file...', end='\r')
        newxml.writelines(temp_xml_lines)

    print(f'[OK] Results preview at {last_step} s ready!')

    return 0
    



#### ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ####


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
        self.trusses = self.get(0.5)
        self.beams = self.get(1)
        self.shells = self.get(2)
        self.solids = self.get(3)
        self.beamparameters = self.get_beamparameters()

        # [['profilename.tsh', [material1no, ... materialnno]]]
        # [['profilename.tem', [material1no, ... materialnno]]]
        # ['tempcurve.txt', area, initial_stress, materialno]
        self.beamtypes, self.shelltypes, self.trusstypes = self.get_types()

        self.t_end = self.get_time()

        self.materials = self.get_materials()

    # import entities
    def get(self, entity_type):
        got = []
        keys = []   # [start, element, end (tuple if many options possible)]

        if entity_type in ['node', 'nodes', 'n', 0]:
            keys = ['NODES', 'NODE', ['FIXATIONS']]
            entity_type = 0
        elif entity_type in ['truss', 'trusses', 't', 0.5]:
            keys = ['NODOFTRUSS', 'ELEM', ['NODOFBEAM', 'NODOFSHELL', 'NODOFSOLID', 'PRECISION', 'RELAX_ELEM']]
            entity_type = 0.5
        elif entity_type in ['beam', 'beams', 'b', 1]:
            keys = ['NODOFBEAM', 'ELEM', ['NODOFTRUSS', 'NODOFSHELL', 'NODOFSOLID', 'PRECISION', 'RELAX_ELEM']]
            entity_type = 1
        elif entity_type in ['shell', 'shells', 'sh', 2]:
            keys = ['NODOFSHELL', 'ELEM', ['NODOFTRUSS', 'NODOFBEAM', 'NODOFSOLID', 'PRECISION', 'RELAX_ELEM']]
            entity_type = 2
        elif entity_type in ['solid', 'solids', 'sd', 3]:
            keys = ['NODOFSOLID', 'ELEM', ['NODOFTRUSS', 'NODOFBEAM', 'NODOFSHELL', 'PRECISION', 'RELAX_ELEM']]
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

    def get_beamparameters(self, update=False):
        """ beamparameters mostly say in which line specific data appears.
                IMPORTANT! table of data starts from 0 -> lines in notepad will be greater by 1
        """
        beamparameters = {}

        beamparameters['BEAM'] = [x for x in range(len(self.file_lines)) if 'BEAM' in self.file_lines[x]][0]  #where beam line appears (begining of the file)

        for x in range(len(self.file_lines)):
            if 'NODOFBEAM' in self.file_lines[x]:
                beamparameters['NODOFBEAM'] = x
            if 'END_TRANS' in self.file_lines[x]:
                beamparameters['END_TRANS_LAST'] = x
            if 'NODES' in self.file_lines[x]:
                beamparameters['nodes'] = x

        beamparameters['elem_start'] = 0
        beamparameters['beamtypes'] = []
        lines = 0
        for line in self.file_lines[beamparameters['NODOFBEAM']:]: #how many lines till ELEM appears- beams ends (every beam has 3 lines)
            if "ELEM" not in line:
                if line.lower().endswith(".tem\n"):
                    beamparameters['beamtypes'].append(line[:-5]) 
                lines+=1
            else:
                #lines+=1
                beamparameters['elem_start'] = beamparameters['NODOFBEAM'] + lines # ELEM starts
                break
        beamparameters['beamnumber'] = len(beamparameters['beamtypes'])

        if update:
            self.beamparameters = beamparameters

        return beamparameters

    def get_types(self):
        check = [-1, -1, -1]
        beams = []
        shells = []
        trusses = []

        read = -1
        b = []
        sh = []
        for line in self.file_lines:
            if 'BEAM' in line and check[0] >= 0:
                check[0] = int(line.split()[-1])
            elif 'SHELL' in line and not check[1] >= 0:
                check[1] = int(line.split()[-1])
            elif 'TRUSS' in line and not check[2] >= 0:
                check[2] = int(line.split()[-1])

            elif 'NODOFBEAM' in line:
                read = 0
            elif 'NODOFSHELL' in line:
                read = 1
            elif 'NODOFTRUSS' in line:
                read = 2

            # read beamtypes
            elif read == 0:
                if 'tem' in line.lower():
                    b = [line.split()[0], []]
                elif 'TRANSLATE' in line:
                    b[1].append(line.split()[-1])
                elif 'END_TRANS' in line:
                    beams.append(b)
                elif 'ELEM' in line:
                    read = -1

            # read shelltypes
            elif read == 1:
                if 'tsh' in line.lower():
                    sh = [line.split()[0], []]
                elif 'TRANSLATE' in line:
                    sh[1].append(line.split()[-1])
                elif 'END_TRANS' in line:
                    shells.append(sh)
                elif 'ELEM' in line:
                    read = -1

            # read trusstypes
            elif read == 2:
                if 'ELEM' in line:
                    read = -1
                    continue
                spltd = line.split()
                trusses.append([spltd[0], *[float(i) for i in spltd[1:-1]], int(spltd[-1])])

        return beams, shells, trusses

    def get_materials(self):
        materials = []      # [['mat1name', [par1, ..., parn], ...]
        m = []
        r = False
        for line in reversed(self.file_lines):
            if r:
                spltd = line.split()
                if len(spltd) > 1:
                    m.append([float(p) for p in spltd])
                elif len(spltd) == 1:
                    if spltd[0] == 'MATERIALS':
                        return materials
                    m.insert(0, spltd[0])
                    materials.append(m)
                    m = []
                else:
                    continue

            elif all(['TIME' in line, 'TIMEPRINT' not in line, 'END' not in line]):
                r = True

    def move(self, vector):
        for n in self.nodes:
            l = self.file_lines[self.beamparameters['nodes']+int(n[0])].split()
            for i in range(3):
                n[i+1] = n[i+1] + vector[i]
                l[i+2] = str(float(l[i+2]) + vector[i])
                self.file_lines[self.beamparameters['nodes']+int(n[0])] = '\t'.join(l) + '\n'

    def save_line(self, name, path='.'):
        with open(os.path.join(path, name), 'w') as file:
            file.writelines(self.file_lines)



# ================ new API-like part for SAFIR input files ===============
# vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class Entity:
    def __init__(self):
        self.tag = int
        self.value = []
        self.dim = int
        self.prop = str if self.dim > 0 else None

        #                           node (dim=0)   |  beam (dim=1)    | shell (dim=2)
        self.load = []  # [Px, Py, Pz, Mx, My, Mz] | [qx, qy, qz]     | [qarea]
        self.mass = []  # [m1, m2, m3, m4, m5, m6] | [m, rot_inertia] | [mass]

        self.fix = []   # [1 for fixation, 0 for not fixed]

        self.relax = []     # [relxation parameters]

    
class Entities:
    def __init__(self):
        self.dim = int
        self.entities = []  # list of Entity objects
        self.taglist = self.dotaglist()
        self.numlist = self.taglist.values()

        # properties
        self.proprties = Propeties(self.dim)


    # return dictionary of entities with tags as keys
    def dotagdict(self):
        tag_dict = {}
        for e in self.entities:
            tag_dict[str(e.tag)] = e.value

        return tag_dict


class Nodes(Entities):
    def __init__(self):
        super().__init__(self)
        self.dim = 0


class Beams(Entities):
    def __init__(self):
        super().__init__(self)
        self.dim = 1
        self.profiletag = int 
        # self.relax = {}     # {'tag': [relaxation parameters (float)], ... }


class Shells(Entities):
    def __init__(self):
        super().__init__(self)
        self.dim = 2
        self.vert = 4      # number of vertices (quad elements are default)
        self.tshtag = int

        # conditions
        self.frontiers = [None, None, None, None]     # [FUNC1, FUNC2, FUNC3, FUNC4]
        self.flux = [None, None, None, None]     # [FUNC1, FUNC2, FUNC3, FUNC4]
        self.temp = [None, None, None, None]     # [FUNC1, FUNC2, FUNC3, FUNC4]
        self.void = [None, None, None, None]     # [FUNC1, FUNC2, FUNC3, FUNC4]
        

class Solids(Entities):
    def __init__(self):
        super().__init__(self)
        self.dim = 2
        self.vert = 8      # number of vertices (hexahedral elements are default)
        
        # there should be some temperature constraints also


class Geometry:
    def __init__(self, n=None, b=None, sh=None, sd=None):
        self.nodes = n
        self.beams = b
        self.shells = sh
        self.solids = sd

        self.profiles = {} # list of profiles {'b': {'profile': [globalmat1, globalmat2 ... ] ... }, 'sh': {...}}

    def read(self, file_lines, dim=None):
        # read entities form file lines
        # possible to read only chosen dimensions
        pass
    
    def write(self, file_lines=None, mode=None, dim=None):
        # return geometry lines entities form file lines
        # possible to write only chosen dimensions
        # possible to write (append or replace) geometry in filelines
        pass

# 
# class Thermal2D(Properties):
#     def __init__(self):
#         super().__init__(self)
#         self.frontiers = {}   # {'TAG':[FUNC1, FUNC2, FUNC3, FUNC4] ... ]
#         self.flux = {}   # {'TAG':[FUNC1, FUNC2, FUNC3, FUNC4] ... ]
#         self.temp = {}   # {'TAG':[FUNC1, FUNC2, FUNC3, FUNC4] ... ]
# 
#         
# 
# class Thermal3D(Properties):
#     def __init__(self):
#         super().__init__(self)
#         self.frontiers = {}   # {'TAG':[FUNC1, FUNC2, FUNC3, FUNC4] ... ]
#         self.flux = {}   # {'TAG':[FUNC1, FUNC2, FUNC3, FUNC4] ... ]
#         self.temp = {}   # {'TAG':[FUNC1, FUNC2, FUNC3, FUNC4] ... ]
# 
# 
# class ThermalTSH(Properties):
#     def __init__(self):
#         super().__init__(self)
#         self.frontiers = {}   # {'TAG':[FUNC1, FUNC2, FUNC3, FUNC4] ... ]
#         self.flux = {}   # {'TAG':[FUNC1, FUNC2, FUNC3, FUNC4] ... ]
#         self.temp = {}   # {'TAG':[FUNC1, FUNC2, FUNC3, FUNC4] ... ]
# 
# # # class Structural2D(Properites): #     def __init__(self):
#         super().__init__(self)
#         self.loads = {}
#         self.masses = {}
# 
# 
# class Structural3D(Properites):
#     def __init__(self):
#         super().__init__(self)
#         pass
# 

# to be developed in the future: one material in SAFIR = one class
class Material:
    def __init__(self):
        self.name = str
        self.parameters = []    # list of parameters required by SAFIR for the Material


class NewInFile:
    def __init__(self, problemtype: str, chid=None, path=None):
        # file data
        self.chid = chid if chid else None
        self.path = path if path else None
        self.lines = []
        
        self.pt = problemtype

        # geometry
        self.geom = Geometry()

        # simulation
        self.nfiber = 440   # default GiD number
        self.time_end = 1800    # default
        self.algorithm = 1      # 1 for PARDISO, 0 for CHOLESKY
        self.cores = 1  # valid only if self.algorithm == 1
        self.description = 'SAFIR simulaion produced with safir_tools.py\nvisit'\
                            'github.com\kowalskiw\\fireeng-tools for more details'
        self.materials = [] # list of Material objects



        
    def read_lines(self, path):
        with open(path) as f:
            self.lines = f.readlines()
        
        self.path = path
        self.chid = '.'.join(os.basename(path).split('.')[:-1])

    def read_sim(self, path=None):
        p = self.path if not path else path
        read_lines(p)
        read_data()

    def read_data(self):
        pass
    
    # save lines to path
    def write_lines(self, path, update=True):
        self.update_lines() if update else None
        with open(path, 'w') as f:
            f.writelines(self.lines)
        

    # replace lines with current data
    def update_lines(self):
        pass


class Thermal2d(NewInFile):
    def __init__(self):
        super().__init__(self, 'Thermal2D')

# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



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

