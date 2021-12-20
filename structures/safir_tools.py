import subprocess
from os import getcwd, chdir

from xml.dom.minidom import parse as pxml

# running SAFIR simulation
from os.path import dirname, basename


def run_safir(in_file_path, safir_exe_path='C:\SAFIR\safir.exe', print_time=True):
    backpath = getcwd()
    chdir(dirname(in_file_path))
    chid = basename(in_file_path)[:-3]

    process = subprocess.Popen(' '.join([safir_exe_path, chid]), shell=False, stdout=subprocess.PIPE)
    print_all = False
    success = True
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
            # check for timestep
            elif 'time' in output and print_time:
                print('%s %s' % ('SAFIR started "{}" calculations: '.format(chid), output), end='\r')

    rc = process.poll()
    chdir(backpath)

    if not rc:
        if success:
            print('[OK] SAFIR finished "{}" calculations at'.format(chid))
            return 0
        else:
            print('[WARNING] SAFIR finished "{}" calculations with error!'.format(chid))
            return -1


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
        nodes = [None]
        point = []
        for node in self.doc.getElementsByTagName('NODES')[0].childNodes[1:-1:2]:
            if node.nodeName == 'N':
                point = []
                for p in node.childNodes[1:-1:2]:
                    print(p)
                    point.append(p.firstChild.data)

            nodes.append(point) if len(point) == 3 else None

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

    return InFile(path.basename[:-3], f, type=None)


class InFile:
    def __init__(self, chid, file_lines, type=None):
        self.file_lines = file_lines
        self.chid = chid
        self.type = 'type_of_analysis'
        self.nodes = self.get(0)
        self.beams = self.get(1)
        self.shells = self.get(2)
        self.solids = self.get(3)

    # import entities
    def get(self, entity_type):
        got = [self.chid]
        keys = []   # [start, element, end (tuple if many options possible)]

        if entity_type in ['node', 'nodes', 'n', 0]:
            keys = ['NODES', 'NODE', ['FIXATIONS']]
        elif entity_type in ['beam', 'beams', 'b', 1]:
            keys = ['NODOFBEAM', 'ELEM', ['NODOFSHELL', 'NODOFSOLID', 'PRECISION']]
        elif entity_type in ['shell', 'shells', 'sh', 2]:
            keys = ['NODOFSHELL', 'ELEM', ['NODOFBEAM', 'NODOFSOLID', 'PRECISION']]
        elif entity_type in ['solid', 'solids', 'sd', 3]:
            keys = ['NODOFSOLID', 'ELEM', ['NODOFBEAM', 'NODOFSHELL', 'PRECISION']]

        read = False
        for line in self.file_lines:
            if keys[0] in line:
                read = True
            elif read and keys[1] in line:
                got.append([int(i) for i in line.split()[1:]])  # first element of list is entity number
            elif read and any(stop in line for stop in keys[2]):
                break

        return got

