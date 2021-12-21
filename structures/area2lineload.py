# script changing area load to beam (line) load
# already drafted - to be developed
#
# import DXF surfaces and area loads assigned to them - surface should be created with lines exactly matching
#   beams (lines) to be loaded
#
# make Safir Structural 3D dummy shells corresponding to imported surfaces (make geometry, assign loads [F1] and
#   very rigid material, constraint all edge-nodes)
#
# run SAFIR mechanical calculations (STATICCOLD APPR NR) with two or three time steps and thick shell section (no
#   heating); use small initial time step and allow choosing relative number of dummy shell elements
#
# process the results of all calculations, find reactions values in OUT or XML file, assign them to node coordinates,
#   sum loads according to DOF, save in CSV file
#
# import Safir Structural 3D file with the structure you want to be loaded
#
# find matching nodes with given precision (quite small I think) and assign already calculated loads to them
#
# export loaded IN file
import os
from math import sqrt, isclose
from os import scandir
import dxfgrabber
from safir_tools import run_safir, ReadXML, read_in
import gmsh
from numpy import interp

# dummy shell template to present area of loading with marked places to insert data
sh_template = ['Dummy file generated with area2lineload.py\n',
               'Check our github: kowalskiw/fireeng-tools!\n',
               '\n',
               '     NNODE    ???\n', # here number of elements [-6]
               '      NDIM    3\n',
               '   NDOFMAX    7\n'
               '    NCORES    4\n'
               '   STATICCOLD   APPR_NR\n'
               '     NLOAD    3\n'
               '   OBLIQUE    0 \n'
               '  COMEBACK 0.0001\n'
               '   NORENUM\n'
               '      NMAT    1\n'
               'ELEMENTS\n'
               '     SHELL     ???     1\n'  # here number of elements [-5]
               '   NGTHICK    8\n'
               '    NGAREA    2\n'
               '   NREBARS    0 \n'
               '  END_ELEM\n'
               '     NODES\n',
               '      ???',  # here all nodes generated [-4]
               ' FIXATIONS\n',
               '  ???',  # here all edges fixed with all DOF [-3]
               '   END_FIX\n',
               'NODOFSHELL\n',
               'dummy.tsh\n',
               '  TRANSLATE    1    1\n',
               'END_TRANS\n',
               '???',   # here elements [-2]
               'PRECISION 1.0e-3 \n',
               'LOADS\n',
               'FUNCTION FLOAD\n',
               '???',  # here area loads [-1]
               'END_LOAD\n',
               ' MATERIALS\n',
               'STEELEC32D\n',
               '           2.10e+11   3.00e-01   2.50e+10  1200.   0.\n',
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
dummy_tsh = [' THICKNESS    0.500\n',
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


def distance(a, b): return sqrt(sum([(a[i] - b[i]) ** 2 for i in range(3)]))


def is_between(a, c, b): return isclose(distance(a, c) + distance(c, b), distance(a, b))


# return list of [shell points tuple, layer name] for each face (3DFACE and POLYFACE) in DXF
def dxf_import(dxffile_path: str):
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
    dxf = dxfgrabber.readfile(dxffile_path)
    def loads_from_layer(layername): return [float(l) for l in layername.split()]

    # find areas and their layernames
    for ent in dxf.entities:
        if ent.dxftype == '3DFACE':
            areas.append([ent.points, loads_from_layer(ent.layer)])
        elif ent.dxftype == 'POLYFACE':
            areas.append([merge_polyface(ent), loads_from_layer(ent.layer)])

    return areas    # vertices needs to be ordered properly to join them in loop one by one


# require edge points tuple to be order right 1->2->...->n-1->n
def make_shell(vertices: list[tuple], element_size: float=None):
    gmsh.initialize()
    gmsh.model.add('dummy_shell')
    shell = gmsh.model

    # create points
    pts = [shell.geo.addPoint(*v) for v in vertices]

    # create lines
    lines = []
    for i in range(len(pts)):
        try:
            lines.append(shell.geo.addLine(pts[i], pts[i+1]))
        except IndexError:
            lines.append(shell.geo.addLine(pts[-1], pts[0]))

    # create surface with quadrilateral mesh type
    surf = shell.geo.addPlaneSurface([shell.geo.addCurveLoop(lines)])
    shell.geo.synchronize()
    shell.mesh.setRecombine(2, surf)

    # create mesh
    shell.mesh.setSize(shell.getEntities(), element_size) if element_size else None
    shell.mesh.generate(2)

    # get mesh data
    nodes = []
    gmsh_nodes = shell.mesh.getNodes()
    for n in range(len(gmsh_nodes[0])):
        nodes.append([gmsh_nodes[1][i] for i in [3*n, 3*n+1, 3*n+2]])

    elements = []
    gmsh_elements = shell.mesh.getElementsByType(3)
    for e in range(len(gmsh_elements[0])):
        elements.append([gmsh_elements[1][i] for i in [4*e, 4*e+1, 4*e+2, 4*e+3]])

    gmsh.finalize()

    return nodes, elements


# method to be extended for unstructured meshes
def find_edges(mesh_nodes: list[list], geom_points: list[tuple]):
    geom_points = [* geom_points, geom_points[0]]
    edges = []

    for xtag, coords in enumerate(mesh_nodes):
        for i in range(len(geom_points)-1):
            if is_between(geom_points[i], coords, geom_points[i+1]) and xtag+1 not in edges:
                edges.append(xtag + 1)

    return edges    # list of edge nodes tags


# produce and save Safir Structural 3D input file with one shell
def dummy_area(points: list[tuple], load: list, n: int, pathtodir='.'):
    node_template = ['      NODE     ', '  \n']
    element_template = ['      ELEM     ', '   1  \n']
    fix_template = ['     BLOCK     ', '   F0   F0   F0   F0   F0   F0   F0\n']
    load_template = [' DISTRSH    ', '\n']
    dummy_sh = ''.join(sh_template).split('???')
    nodes, elements = make_shell(points)

    edges = find_edges(nodes, points)     # edge nodes tags

    dummy_sh.insert(-6, str(len(nodes)))
    dummy_sh.insert(-5, str(len(elements)))

    # define nodes
    for xtag, coords in enumerate(nodes):
        n_line = node_template.copy()
        [n_line.insert(-1, str(i)) for i in [xtag+1, *coords]]
        print(n_line)
        dummy_sh.insert(-4, '   '.join(n_line))

    # fix edge nodes
    for ed_tag in edges:
        fix_line = fix_template.copy()
        fix_line.insert(-1, str(ed_tag))

        dummy_sh.insert(-3, '   '.join(fix_line))

    # define elements
    for xtag, nodes_tags in enumerate(elements):
        e_line = element_template.copy()
        [e_line.insert(-1, str(i)) for i in [xtag+1, *nodes_tags]]

        dummy_sh.insert(-2, '   '.join(e_line))

    # load all elements
    for e in elements:
        l_line = load_template.copy()
        [l_line.insert(-1, str(i)) for i in [e[1], *load]]

        dummy_sh.insert(-1, '   '.join(l_line))

    with open('{}\dummy_{}.in'.format(pathtodir, n), 'w') as d:
        d.write(''.join(dummy_sh))


# map element with load
# points => [[x,y,z] (x3 for start, middle and end)]
# lineloads => [[p1: list(len=3), r1: list(len=7)], [p2, r2], ... [pn, rn]]
def map_l2e(points: list, reactions: list[list[list]]):
    e_load = []  # summary line load per element with given endpoints
    d1, d2 = (999, 999)

    # find the nearest reaction point
    to_inter = [None, None]
    for r in reactions:
        d_r = distance(r[0], points[1])
        if d_r < d1:
            to_inter[0] = r

    # find opposite point
    for r in reactions:
        if is_between(to_inter[0], points[1], r[0]):
            d_r = distance(r[0], points[1])
            if d_r < d2:
                to_inter[1] = r

    for dof in range(7):    # for every DOF
        lineload = interp(0, [-d1, d2], [to_inter[i][dof] for i in (0, 1)])/distance(points[0], points[2])
        e_load.append(lineload)

    return e_load


# process dummy results data
def gather_results(pathtodummies='.'):
    reac_data = []
    for s in scandir(pathtodummies):
        if 'XML' in s.name:
            r = ReadXML(s.path)
            reactions = r.reactions(
                -1)  # [[node_no, [R(node_no)_dof1,...,R(node_no)_dof7],...,[node_no, [R(node_no)_dof1,...,R(node_no)_dof7]]
            nodes = r.nodes()  # [None,[p1x,p1y,p1z],...,[pnx, pny, pnz]]
            for r in reactions:
                reac_data.append([nodes[r[0]], r[1]])

    return reac_data  # [[p1: list(len=3), r1: list(len=7)], [p2, r2], ... [pn, rn]]


# add new load data (lineloads) to the model (infile)
def assign_loads(in_path: str, lineloads: list, function='F1'):
    infile = read_in(in_path)

    converted_loads = ['   FUNCTION {}\n'.format(function), '  END_LOAD\n']
    load_template = ' DISTRBEAM    {}    {}    {}    {}\n'

    # map beam elements to lineloads
    for be in infile.beams:
        points = infile.nodes[be[1:4]]   # start, middle, end point of beam element like [x,y,z]
        elem_loads = map_l2e(points, lineloads)
        converted_loads.insert(-1, load_template.format(be[0], *elem_loads))

    # make new IN file with line loads
    lloaded = infile.file_lines
    for l in lloaded:
        if 'NLOAD' in l:
            lloaded[lloaded.index(l)] = '     NLOAD    {}\n'.format(int(l.split()[-1]) + 1)
        elif 'END_LOAD' in l:
            lloaded = lloaded[:lloaded.index(l) + 1] + converted_loads + lloaded[lloaded.index(l) + 1:]
            break

    with open('{}_ll.in'.format(infile.chid), 'w') as file:
        file.write(''.join(lloaded))


def main(pathtodir, pathtoinfile, pathtodxf):
    calcpath = pathtodir
    infile = pathtoinfile
    areas = dxf_import(pathtodxf)  # list of areas [vertices (tuple), loads value (float)]

    # create dummy structural files for each area
    [dummy_area(*areas[i], i, pathtodir=pathtodir) for i in range(len(areas))]

    # write section thermal (cold) input to calculation directory
    with open('{}\\dummy.tsh'.format(calcpath), 'w') as tem:
        tem.writelines(dummy_tsh)

    # run mech analyses
    # done
    [run_safir('{}\dummy_{}.in'.format(pathtodir, i)) for i in range(len(areas))]

    # postprocess of dummy simulations
    # read reactions from dummy results and save with coordinates of nodes
    # done
    lineloads = gather_results(pathtodummies=pathtodir)

    # assign line loads to beams from IN file:
    # map2le TO BE DONE
    assign_loads(infile, lineloads)


main('D:\\testy\\are2lineload\\test_set\calc\\', 'D:\\testy\\are2lineload\\test_set\\area2line.in',
     'D:\\testy\\are2lineload\\test_set\\areas.dxf')
