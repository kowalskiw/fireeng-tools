# 1. Introduction
#
#   This script allows to convert area loads into beam loads. To implement area load into the beam model you need your
#   Safir Structural 3D input file and loaded areas models (DXF or IGES).
#
#   The user should be familiar with FEM modelling and SAFIR(R) software itself to judge the results properly. The basic
#   knowledge about Python and gmsh package is also required to use and debug the script.
#
#   The script is a part of this repository https://github.com/kowalskiw/fireeng-tools. You can find there some scripts
#   useful in SAFIR(R) structural analysis, as well as in computer fire engineering at all.
#
# 2. Area files
#
#   All area files should be stored in the areas directory - the path of witch is the first argument to running script
#   in command-line.
#
#   Global coordinates systems in areas files (DXF or IGES) must be precisely consistent with SAFIR(R) input file. Each
#   surface in areas files should represent one fully constrained shell. The shell does not need to be constrained on
#   all edges.
#
#   In the area file you have to present surface geometry and area load connected with this area. Depending on the
#   format (DXF or IGES) defining those areas differs.
#
#
#   2.1. DXF format - planar surfaces only, faster
#
#       Load areas should be represented with "3DFACE" (3 or 4 nodes) or "POLYSURFACE" (> 4 nodes). Every surface should
#       be assigned to the layer, which defines the load connected to the surface.

#       The information about load values is stored in layer name. SI units [N/m2] should be used The proper notation of
#       load is: "[X pressure] [Y pressure] [Z pressure]".
#       Example: surface representing floor loaded with 3,5 kN/m2 should be assigned to "0 0 -3500" layer.
#       Surfaces with the same load pattern can be assigned to the same layer.
#
#       In order to enable surfaces to be supported with not all edges, constraints should be defined. Those should be
#       lines ("LINES") assigned to the "edges" layer. These lines should not be a part of any surface defined
#       previously. However coordinates of the edge lines should be consistent with surface edges as well as with beams
#       in SAFIR(R) input file. The edge lines will be used to calculate and map the load along the beam elements from
#       input file.
#
#
#   2.2. IGES format - any type of surface, slower
#
#       Due to missing layer data in importing IGES to gmsh there is a need to split each surface to a single file.
#
#       Load areas can be represented by any surface (2-D entity) type (e.g. "PlanarSurface", "BSplineSurface"...). The
#       only limitation is the gmsh quadrilateral meshing  algorithm, which can miss some elements when the surface has
#       very complex shape.
#
#       Load data should be contained in IGES file name. Naming manner is the same as in DXF files.
#       Example: surface representing floor loaded with 3,5 kN/m2 should be in to "0 0 -3500.iges" or "0 0 -3500.igs"
#       file.
#
#       This analogy in naming is valid also for edge lines. There should be a file "edges.igs" or "edges.iges" where
#       all edges are drawn as curves (1-D entities) of any type ("Line", "BSpline"...)
#
#
# 3. Running the script
#
#   The script can be run in the command-line and its main function requires two paths as arguments:
#       (a) path to areas directory (where IGES or/and DXF files are stored);
#       (b) path to original Safir Structural 3D input file, whereto loads should be inserted.
#
#   All files produced by script (including converted input file) will be stored in 'out-files' directory.
#   The 'out-files' directory will be created in the same catalogue where original input file is.
#
#
# 4. Missing features
#
#   There are still missing features in the script. One of them is mass conversion for dynamic analysis.
#
#   If you have noticed any bugs or enhancement possibilities feel free to submit an issue or open a pull-request here:
#   https://github.com/kowalskiw/fireeng-tools
import sys
from math import sqrt, isclose
from os import scandir, makedirs, rmdir
from os.path import basename, dirname, abspath
import dxfgrabber
from safir_tools import run_safir, ReadXML, read_in
import gmsh
from numpy import interp


def distance(a, b): return sqrt(sum([(a[i] - b[i]) ** 2 for i in range(3)]))


def is_between(a, c, b): return isclose(distance(a, c) + distance(c, b), distance(a, b), rel_tol=0.0001)


class DummyShell:
    def __init__(self, number: int, path_to_file: str, element_size: float = None, calcdir=None):
        # dummy shell template to present area of loading with marked places to insert data
        self.template = ['Dummy file generated with area2lineload.py\n',
                         'Check our github: kowalskiw/fireeng-tools\n',
                         '\n',
                         '     NNODE    ???\n',  # here number of elements [-6]
                         '      NDIM    3\n',
                         '   NDOFMAX    7\n',
                         '    NCORES    4\n',
                         '   STATICCOLD   APPR_NR\n',
                         '     NLOAD    1\n',
                         '   OBLIQUE    0 \n',
                         '  COMEBACK 0.0001\n',
                         '   NORENUM\n',
                         '      NMAT    1\n',
                         'ELEMENTS\n',
                         '     SHELL     ???     1\n',  # here number of elements [-5]
                         '   NGTHICK    8\n',
                         '    NGAREA    2\n',
                         '   NREBARS    0 \n',
                         '  END_ELEM\n',
                         '     NODES\n',
                         '      ???',  # here all nodes generated [-4]
                         ' FIXATIONS\n',
                         '  ???',  # here all edges fixed with all DOF [-3]
                         '   END_FIX\n',
                         'NODOFSHELL\n',
                         'dummy.tsh\n',
                         '  TRANSLATE    1    1\n',
                         'END_TRANS\n',
                         '???',  # here elements [-2]
                         'PRECISION 1.0e-3 \n',
                         'LOADS\n',
                         'FUNCTION F1\n',
                         '???',  # here area loads [-1]
                         'END_LOAD\n',
                         ' MATERIALS\n',
                         'STEELEC32D\n',
                         '           9e+12   3.00e-01   9e+12  1200.   0.\n',
                         'TIME\n',
                         '1.0     10.0      \n',
                         'ENDTIME\n',
                         'EPSTH\n',
                         'IMPRESSION\n',
                         'TIMEPRINT\n',
                         '1.0     10.0      \n',
                         'END_TIMEPR\n',
                         'PRINTREACT\n'
                         ]

        # cold section results to be written as an input for mechanical analysis
        self.section = ['\n',
                        ' THICKNESS    0.500\n',
                        '  MATERIAL    1\n',
                        '  REBARS    0\n',
                        '\n',
                        ' COLD\n',
                        ' POSITIONS OF THE NODES.\n',
                        ' =======================\n',
                        ' NUMBER OF POSITIONS:  51\n',
                        ' -0.2500E+00 -0.2400E+00 -0.2300E+00 -0.2200E+00 -0.2100E+00 -0.2000E+00 -0.1900E+00 -0.1800E+00\n',
                        ' -0.1700E+00 -0.1600E+00 -0.1500E+00 -0.1400E+00 -0.1300E+00 -0.1200E+00 -0.1100E+00 -0.1000E+00\n',
                        ' -0.9000E-01 -0.8000E-01 -0.7000E-01 -0.6000E-01 -0.5000E-01 -0.4000E-01 -0.3000E-01 -0.2000E-01\n',
                        ' -0.1000E-01  0.0000E+00  0.1000E-01  0.2000E-01  0.3000E-01  0.4000E-01  0.5000E-01  0.6000E-01\n',
                        '  0.7000E-01  0.8000E-01  0.9000E-01  0.1000E+00  0.1100E+00  0.1200E+00  0.1300E+00  0.1400E+00\n',
                        '  0.1500E+00  0.1600E+00  0.1700E+00  0.1800E+00  0.1900E+00  0.2000E+00  0.2100E+00  0.2200E+00\n',
                        '  0.2300E+00  0.2400E+00  0.2500E+00\n']

        self.no = number
        self.elsize = element_size
        self.filepath = path_to_file  # path to DXF (dxf=True) or IGES (dxf=False) file
        self.dirpath = dirname(path_to_file)  # path to calculation directory
        self.calcdir = calcdir if calcdir else self.dirpath

        self.load = []  # [x_pressure, y_pressure, z_pressure] [N/m2]

        # self.nodes = [tag, x, y, z]    self.elements = [tag, node1, node2, node3, node4]
        self.nodes, self.elements = self.geometry()

    def geometry(self):
        nodes = []
        elements = []

        return nodes, elements  # [[[x1,y1,z1]], ... n]   [[[nodetag1,nodetag1, ... nodetagm]], ... n]

    def edges(self):
        edges = []

        return edges

    def write(self):
        node_template = ['      NODE     ', '  \n']
        element_template = ['      ELEM     ', '   1  \n']
        fix_template = ['     BLOCK     ', '   F0   F0   F0   F0   F0   F0   F0\n']
        load_template = [' DISTRSH    ', '\n']
        dummy_sh = ''.join(self.template).split('???')

        edgetags = self.edges()  # edge nodes tags [[start point of edge 1, endpoint of edge 1], ... n]

        dummy_sh.insert(-6, str(len(self.nodes)))
        dummy_sh.insert(-5, str(len(self.elements)))

        # define nodes
        for xtag, coords in enumerate(self.nodes):
            n_line = node_template.copy()
            [n_line.insert(-1, str(i)) for i in [xtag + 1, *coords]]
            dummy_sh.insert(-4, '   '.join(n_line))

        # fix edge nodes
        for tag in edgetags:
            fix_line = fix_template.copy()
            fix_line.insert(-1, str(tag))

            dummy_sh.insert(-3, '   '.join(fix_line))

        # define elements
        for xtag, nodes_tags in enumerate(self.elements):
            e_line = element_template.copy()
            [e_line.insert(-1, str(i)) for i in [xtag + 1, *nodes_tags]]

            dummy_sh.insert(-2, '   '.join(e_line))

        # load all elements
        for xtag in range(len(self.elements)):
            l_line = load_template.copy()
            [l_line.insert(-1, str(i)) for i in [xtag + 1, *self.load]]

            dummy_sh.insert(-1, '   '.join(l_line))

        with open('{}\dummy_{}.in'.format(self.calcdir, self.no), 'w+') as d:
            d.write(''.join(dummy_sh))

        if 'dummy.tsh' not in scandir(self.calcdir):
            with open('{}\dummy.tsh'.format(self.calcdir), 'w') as d:
                d.writelines(self.section)

    def run(self):
        run_safir('{}\dummy_{}.in'.format(self.calcdir, self.no))


class DummyShellIGES(DummyShell):
    # geometry from iges file, mesh generated with gmsh, loads from filename
    def geometry(self):
        gmsh.initialize()
        gmsh.model.add('dummy')
        shell = gmsh.model
        shell.occ.importShapes(self.filepath)
        shell.occ.synchronize()

        # recombine meshes (triangle mesh -> quadrilateral mesh)
        try:
            i = 1
            while True:
                shell.mesh.setRecombine(2, i)
                i += 1
        except Exception:
            pass

        # create mesh
        gmsh.option.setNumber("Mesh.Algorithm", 8)
        gmsh.option.setNumber("Mesh.RecombinationAlgorithm", 3)
        shell.mesh.setRecombine(2, 1)
        shell.mesh.setSize(shell.getEntities(), self.elsize) if self.elsize else None
        shell.mesh.generate(2)

        # get mesh data
        nodes = []
        gmsh_nodes = shell.mesh.getNodes()
        for n in range(len(gmsh_nodes[0])):
            nodes.append([gmsh_nodes[1][i] for i in [3 * n, 3 * n + 1, 3 * n + 2]])

        elements = []
        gmsh_elements = shell.mesh.getElementsByType(3)
        for e in range(len(gmsh_elements[0])):
            elements.append([gmsh_elements[1][i] for i in [4 * e, 4 * e + 1, 4 * e + 2, 4 * e + 3]])



        gmsh.finalize()

        # add load attribute from IGES filename
        self.load = [float(i) for i in '.'.join(basename(self.filepath).split('.')[:-1]).split()]

        return nodes, elements  # [[[x1,y1,z1]], ... n]   [[[nodetag1,nodetag1, ... nodetagm]], ... n]

    # read edges from iges 'edges' file
    def edges(self):
        gmsh.initialize()
        gmsh.model.add('edges')
        gmsh.model.occ.importShapes('{}\\edges.igs'.format(self.dirpath))
        gmsh.model.occ.synchronize()

        # find nodes of meshed edgelines
        gmsh.model.mesh.generate()
        nodes = gmsh.model.mesh.getNodes()

        edgenodes = []  # find edge nodes coordinates
        [edgenodes.append(list(nodes[1][n:n + 3])) for n in range(0, 3 * len(nodes[0]), 3)]

        edgetags = []  # find edge nodes tags in mesh of dummy shell
        for en in edgenodes:
            try:
                edgetags.append(self.nodes.index(en) + 1)
            except ValueError:
                print('[WARNING] {} is not matched as a valid node in dummy shell mesh'.format(en))

        gmsh.finalize()

        return list(set(edgetags))  # [edgenodetag1, edgenodetag2, ... edgenodetagn]


class DummyShellDXF(DummyShell):
    def __init__(self, number: int, path_to_file: str, element_size: float = None, calcdir: str = None):
        super().__init__(number, path_to_file, element_size=element_size, calcdir=calcdir)
        self.dxf = dxfgrabber.readfile(self.filepath)

    # geometry from dxf file, mesh generated with gmsh, loads from layer name
    def geometry(self):
        # return list of [shell points tuple, layer name] for each face (3DFACE and POLYFACE) in DXF
        def import_shells(dxffile):
            def merge_polyface(polyface):
                subfaces = list(polyface.__iter__())
                merged_face_vertices = list(subfaces[0].__iter__())
                subfaces = subfaces[1:]

                no = 0
                while len(subfaces) > 0:
                    face = subfaces[no]
                    f_vertices = list(face.__iter__())
                    matched = 0
                    i_s = []
                    for j, v in enumerate(merged_face_vertices):
                        if v in f_vertices:
                            i_s.append(j)
                            f_vertices.remove(v)
                            matched += 1

                    if matched == 2:
                        if abs(i_s[1] - i_s[0]) > 1:
                            [merged_face_vertices.append(v) for v in f_vertices]
                        else:
                            [merged_face_vertices.insert(i_s[0] + 1, v) for v in f_vertices]
                        subfaces.remove(face)

                    elif len(f_vertices) == 0:
                        [merged_face_vertices.remove(merged_face_vertices[v]) for v in i_s[1:-1]]
                        subfaces.remove(face)

                    if no >= len(subfaces) - 1:
                        no = 0
                    else:
                        no += 1

                return merged_face_vertices

            areas = []

            def loads_from_layer(layername):
                return [float(ld) for ld in layername.split()]

            # find areas and their layernames
            for ent in dxffile.entities:
                if ent.dxftype == '3DFACE':
                    areas.append([ent.points, loads_from_layer(ent.layer)])
                elif ent.dxftype == 'POLYFACE':
                    areas.append([merge_polyface(ent), loads_from_layer(ent.layer)])

            return areas  # vertices needs to be ordered properly to join them in loop one by one

        dxf_areas = import_shells(self.dxf)[self.no]  # area properties [vertices (tuple),  xyz pressures (list)]
        gmsh.initialize()
        gmsh.model.add('dummy_shell')
        shell = gmsh.model

        # create points
        pts = [shell.geo.addPoint(*v) for v in dxf_areas[0]]

        # create lines
        lines = []
        for i in range(len(pts)):
            try:
                lines.append(shell.geo.addLine(pts[i], pts[i + 1]))
            except IndexError:
                lines.append(shell.geo.addLine(pts[-1], pts[0]))

        # create surface with quadrilateral mesh type
        surf = shell.geo.addPlaneSurface([shell.geo.addCurveLoop(lines)])
        shell.geo.synchronize()
        shell.mesh.setRecombine(2, surf)

        # create mesh
        shell.mesh.setSize(shell.getEntities(), self.elsize) if self.elsize else None
        shell.mesh.generate(2)

        # get mesh data
        nodes = []
        gmsh_nodes = shell.mesh.getNodes()
        for n in range(len(gmsh_nodes[0])):
            nodes.append([gmsh_nodes[1][3 * n + i] for i in range(3)])

        elements = []
        gmsh_elements = shell.mesh.getElementsByType(3)
        for e in range(len(gmsh_elements[0])):
            elements.append([gmsh_elements[1][4 * e + i] for i in range(4)])

        gmsh.finalize()

        # add load attribute from DXF layers names
        self.load = dxf_areas[1]

        return nodes, elements  # [[tag1, [x1,y1,z1]], ... n]   [[tag1, [nodetag1,nodetag1, ... nodetagm]], ... n]

    # read edges from dxf file layer 'edges'
    def edges(self):
        edges = []

        for e in self.dxf.entities:
            if e.layer.lowercase() == 'edges' and e.dxftype == 'LINE':
                edges.append([e.start, e.end])

        # import geometry from dxf file to gmsh
        gmsh.initialize()
        gmsh.model.add('edges')
        occ = gmsh.model.occ
        for xtag, e in enumerate(edges):
            [occ.addPoint(*e[i], xtag+1+i) for i in range(2)]
            occ.addLine(xtag+1, xtag+2)
        occ.synchronize()

        # find nodes of meshed edgelines
        gmsh.model.mesh.generate()
        nodes = gmsh.model.mesh.getNodes()

        edgenodes = []  # find edge nodes coordinates
        [edgenodes.append(list(nodes[1][n:n + 3])) for n in range(0, 3 * len(nodes[0]), 3)]

        edgetags = []  # find edge nodes tags in mesh of dummy shell
        for en in edgenodes:
            try:
                edgetags.append(self.nodes.index(en) + 1)
            except ValueError:
                print('[WARNING] {} is not matched as a valid node in dummy shell mesh'.format(en))

        gmsh.finalize()

        return edgetags  # [edgenodetag1, edgenodetag2, ... edgenodetagn]


class Convert:
    def __init__(self, path_to_areas: str, path_to_in: str):
        self.paths = {'areas': path_to_areas, 'infile': path_to_in, 'calc': '{}\\out-files'.format(dirname(path_to_in))}
        try:
            rmdir(self.paths['calc'])
        except FileNotFoundError:
            pass
        makedirs(self.paths['calc'])

    def prepare_dummies(self):
        i = 0
        dummies = []
        for a in scandir(self.paths['areas']):
            if a.is_file() and 'edges' not in a.name:
                if a.name.lower().endswith('.dxf'):
                    dummies.append(DummyShellDXF(i, a.path, calcdir=self.paths['calc']))
                elif any([a.name.lower().endswith(ext) for ext in ['.igs', '.iges']]):
                    dummies.append(DummyShellIGES(i, a.path, calcdir=self.paths['calc']))

        return dummies

    def run_dummies(self):
        for d in self.prepare_dummies():
            d.write()
            d.run()

    def read_results(self):
        reac_data = []
        for s in scandir(self.paths['calc']):
            if all(i in s.name for i in ['XML', 'dummy']):
                dum_reac = [s.name.split('_')[-1][:-4]]
                r = ReadXML(s.path)
                # [[node_no, R(node_no)_dof1,...,R(node_no)_dof7],...,[node_no, R(node_no)_dof1,...,R(node_no)_dof7]]
                reactions = r.reactions(-1)
                nodes = r.nodes()  # [[p1x,p1y,p1z],...,[pnx, pny, pnz]]
                for r in reactions:
                    dum_reac.append([nodes[r[0] - 1], r[1:]])  # convert node_no to its position in list
                reac_data.append(dum_reac)

        return reac_data  # [[dummy_no, [p1: list(len=3), r1: list(len=NRDOF)], [p2, r2], ... [pn, rn]]]

    def assign_loads(self, reactions: list[list[list]], function='F1', mass=False):
        def map_l2e(points: list, reactions: list[list[list]]):
            e_load = []  # summary line load per element with given endpoints
            d1 = 999
            d2 = 999
            middle = points[1][1:]
            length = distance(points[0][1:], points[2][1:])

            # find the nearest reaction point
            to_inter = [None, None]
            for r in reactions:
                d_r = distance(r[0], middle)
                if all([isclose(middle[i], r[0][i], rel_tol=0.01) for i in range(3)]):
                    return [-load / length for load in r[1]]
                elif d_r < d1:
                    d1 = d_r
                    to_inter[0] = r

            # find opposite point if there is no direct matching between reaction point and middle point of beam
            # check if it is almost between
            for r in reactions:
                if is_between(to_inter[0][0], middle, r[0]):
                    d_r = distance(r[0], middle)
                    if d_r < d2:
                        d2 = d_r
                        to_inter[1] = r

            for dof in range(6):  # for every DOF
                try:
                    lineload = -interp(0, [-d1, d2], [to_inter[i][1][dof] for i in (0, 1)]) / length
                except TypeError:
                    return []
                e_load.append(lineload)

            return e_load

        infile = read_in(self.paths['infile'])
        lloaded = infile.file_lines
        load_template = ' DISTRBEAM    {}    {}    {}    {}\n'
        mass_template = '    M_BEAM    {}    {}    2\n'

        # map beam elements to lineloads from each dummyfile
        for dummy in reactions:
            converted_loads = ['   FUNCTION {}\n'.format(function), '  END_LOAD\n']
            for be in infile.beams:
                # start, middle, end point of beam element like [x,y,z]
                # convert node_no to its position in node list (-1)
                points = [infile.nodes[int(i) - 1] for i in be[1:4]]
                elem_loads = map_l2e(points, dummy[1:])     # mapping function
                converted_loads.insert(-1, load_template.format(be[0], *elem_loads)) if elem_loads else None

            # make new IN file with converted loads
            for line in lloaded:
                if 'NLOAD' in line:
                    lloaded[lloaded.index(line)] = '     NLOAD    {}\n'.format(int(line.split()[-1]) + 1)
                elif 'LOADS' in line:
                    lloaded = lloaded[:lloaded.index(line) + 1] + converted_loads + lloaded[lloaded.index(line) + 1:]
                    break

        with open('{}\{}_ll.in'.format(self.paths['calc'], infile.chid), 'w') as file:
            file.write(''.join(lloaded))

    def convert(self):
        print('[OK] Area to beam load conversion started')
        self.run_dummies()
        print('[OK] Loads calculated')
        self.assign_loads(self.read_results())
        print('[OK] Loads assigned.\n\nThank you for using this script!\n'
              'Visit our GitHub and get involved: https://github.com/kowalskiw/fireeng-tools')


if __name__ == '__main__':
    case = Convert(*[abspath(p) for p in sys.argv[1:]])
    case.convert()
    exit(0)
