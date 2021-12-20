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
from os import scandir
import dxfgrabber
from safir_tools import run_safir, ReadXML, read_in

# dummy shell template to present area of loading with marked places to insert data
sh_template = ['Dummy file generated with area2lineload.py\n',
               'Check our github: kowalskiw/fireeng-tools!\n',
               '     NNODE    50\n',
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
               '     SHELL     ???     1\n'  # here number of elements
               '   NGTHICK    8\n'
               '    NGAREA    2\n'
               '   NREBARS    0 \n'
               '  END_ELEM\n'
               '     NODES\n',
               '      NODE     33 7.50000000E-001 0.00000000E+000 5.12500000E+000\n',  # here all nodes generated
               ' FIXATIONS\n',
               '  ???\n',  # here all edges fixed with all DOF
               '   END_FIX\n',
               'NODOFSHELL\n',
               'dummy.tsh\n',
               '  TRANSLATE    1    4\n',
               'END_TRANS\n',
               '      ELEM   1    19    15    17    20    1\n',
               'PRECISION 1.0e-3 \n',
               'LOADS\n',
               'FUNCTION FLOAD\n',
               'DISTRSH    1    ???    ??? ???\n',  # here area loads
               'END_LOAD\n',
               ' MATERIALS\n',
               'SILCON_ETC\n',
               '            3.00e-01   3.00e+07   2.60e+06\n',
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
tem_template = ''


# return list of [shell points tuple, layer name] for each 3DFACE in DXF
def dxf_import(dxffile: str):
    areas = []
    dxf = dxfgrabber.readfile(dxffile)

    # find areas and their layernames
    for ent in dxf.entities:
        if ent.dxftype == '3DFACE':
            areas.append([ent.points, float(ent.layer)])

    return areas


# produce and save Safir Structural 3D input file with one shell
def make_dummy(points: tuple, load: float, n: int):
    dummy_sh = ''.join(sh_template).split('???')

    # convert data from area element
    # for i in range(len(dummy_sh)):
    # dummy_sh.insert(i, converted(area, load))

    with open('dummy_{}.in'.format(n), 'w') as d:
        d.write(''.join(dummy_sh))


# map element with load
def map_l2e(edges, lineloads):
    e_load = []  # summary line load per element with given edges

    # for i in range(7):    # for every DOF
    #    calculate load at the edges (interpolate 'lineloads' points)
    #    ld = dvide mean load with double element length
    #    e_load.append(ld)

    return e_load


# process dummy results data
def gather_results(pathtodummies='.'):
    reac_data = []
    for s in scandir(pathtodummies):
        if s.isfile() and 'XML' in s.name:
            r = ReadXML(s.path)
            reactions = r.reactions(
                -1)  # [[node_no, [R(node_no)_dof1,...,R(node_no)_dof7],...,[node_no, [R(node_no)_dof1,...,R(node_no)_dof7]]
            nodes = r.nodes()  # [None,[p1x,p1y,p1z],...,[pnx, pny, pnz]]
            for r in reactions:
                reac_data.append([nodes[r[0]], r[1]])

    return reac_data  # [[p1: list(len=3), r1: list(len=7)], [p2, r2], ... [pn, rn]]


# add new load data (lineloads) to the model (infile)
def assign_loads(in_path, lineloads, function='F1'):
    infile = read_in(in_path)

    converted_loads = ['   FUNCTION {}\n'.format(function), '  END_LOAD\n']
    load_pattern = ' DISTRBEAM    {}    {}    {}    {}\n'

    # map beam elements to lineloads
    for be in infile.beams:
        edges = [infile.nodes[n] for n in be[:3]]  # start and end point of beam [[x1,y1,z1],[x2,y2,z2]]
        elem_loads = map_l2e(edges, lineloads)
        converted_loads.insert(-1, load_pattern.format(be[0], *elem_loads))

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


def main():
    calcpath = 'pathtodir'
    infile = 'pathtoinfile'
    areas = dxf_import('pathtodxf')  # import areas and loads

    # create dummy structural files for each area
    # TO BE DONE
    [make_dummy(*areas[i], i) for i in range(len(areas))]

    # write section thermal (cold) input to calculation directory
    # TO BE DONE
    with open('{}\foo.tem'.format(calcpath), 'w') as tem:
        tem.write(tem_template)

    # run mech analyses
    # done
    [run_safir('dummy_{}.in'.format(i)) for i in range(len(areas))]

    # postprocess of dummy simulations
    # read reactions from dummy results and save with coordinates of nodes
    # done
    lineloads = gather_results()

    # assign line loads to beams from IN file:
    # map2le TO BE DONE
    assign_loads(infile, lineloads)
