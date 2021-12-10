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
from safir_tools import run_safir, ReadXML

# dummy shell template to present area of loading with marked places to insert data
sh_template = ''

# cold section results to be written as an input for mechanical analysis
tem_template = ''

def dxf_import(dxffile):
    areas = []
    dxf = dxfgrabber.readfile(dxffile)

    # find areas and their layernames
    for ent in dxf.entities:
        if ent.dxftype == '3DFACE':
            areas.append([ent.points, ent.layer])

    return areas


def make_dummy(area, load, n):
    dummy_sh = sh_template.split('MaRk')

    # convert data from area element
    # for i in range(len(dummy_sh)):
    # dummy_sh.insert(i, converted(area, load))

    with open('dummy_{}.in'.format(n), 'w') as d:
        d.write(''.join(dummy_sh))


# import nodes and elements (optionally materials nos) from IN file
def import_geom(infilelines, withmat=False):
    nodes = ['chid']
    elements = ['chid']
    mats = ['chid'] if withmat else None

    for l in infilelines:
        if 'NODE' in l:
            s = [float(i) for i in l.split()]
            nodes.insert(int(s[1]), s[2:])
        elif 'ELEM' in l:
            s = [int(i) for i in l.split()]
            elements.insert(s[1], s[2:-1])
            mats.insert(s[1], s[-1]) if withmat else None

    return nodes, elements, mats


# map element with load
def map_l2e(edges, lineloads):
    e_load = []    # summary line load per element with given edges

    # for i in range(7):    # for every DOF
    #    calculate load at the edges (interpolate 'lineloads' points)
    #    ld = dvide mean load with element length
    #    e_load.append(ld)

    return e_load


# def read_from_xml(path:str, timestep:int, value:str):
#     rvalues = []
#     temp = []
#     nr = -1

    # with pxml(path) as doc:
    #     reacs = doc.getElementsByTagName(value)
    #
    #     for node in reacs[timestep].childNodes[1:-1:2]:
    #         if node.nodeName == 'N':
    #             temp = []
    #             x = int(node.firstChild.data)
    #             temp.append(int(x))
    #         elif node.nodeName == 'NR':
    #             nr = int(node.firstChild.data)
    #         elif node.nodeName == 'R':
    #             x = float(node.firstChild.data)
    #             temp.append(x)
    #
    #         rvalues.append(temp) if len(temp) == nr else None
    #
    # return rvalues


# process dummy results data
def gather_results(pathtodummies):
    reac_data = []
    for s in scandir(pathtodummies):
        if s.isfile() and 'XML' in s.name:
            r = ReadXML(s.path)
            reactions = r.reactions(-1)     # [[node_no, [R(node_no)_dof1,...,R(node_no)_dof7],...,[node_no, [R(node_no)_dof1,...,R(node_no)_dof7]]
            nodes = r.nodes()   # [None,[p1x,p1y,p1z],...,[pnx, pny, pnz]]
            for r in reactions:
                reac_data.append([nodes[r[0]], r[1]])

    # to be finished



    return reac_data


# add new load data (lineloads) to the model (infile)
def assign_loads(infile, lineloads, function='F1'):
    with open(infile) as f:
        prim_in = f.read()

    converted_loads = ['   FUNCTION {}\n'.format(function), '  END_LOAD\n']

    # import elements
    ns, es, ms = import_geom(prim_in)

    # map elements to lineloads
    for e in es:
        edges = [ns[n] for n in e[:3]]
        loads_elem = map_l2e(edges, lineloads)
        converted_loads.insert(-1, ' DISTRBEAM    {}    {}    {}    {}\n'.format(es.index(e), *loads_elem))

    # make new IN file with line loads
    lloaded = prim_in.splitlines()
    for l in lloaded:
        if 'NLOAD' in l:
            lloaded[lloaded.index(l)] = '     NLOAD    {}\n'.format(int(l.split()[-1]) + 1)
        if 'END_LOAD' in l:
            lloaded = lloaded[:lloaded.index(l) + 1] + converted_loads + lloaded[lloaded.index(l) + 1:]
            break

    with open('{}_ll.in'.format(infile.chid), 'w') as file:
        file.write(''.join(lloaded))


def main():
    calcpath = 'pathtodir'
    infile = 'pathtoinfile'
    # import areas and loads
    areas = dxf_import('pathtodxf')

    # create dummy structural files for each area
    [make_dummy(*areas[i], i) for i in range(len(areas))]

    # write section thermal (cold) input to calculation directory
    with open('{}\foo.tem'.format(calcpath), 'w') as tem:
        tem.write(tem_template)

    # run mech analyses
    [run_safir('dummy_{}.in') for i in range(len(areas))]

    # postprocess of dummy simulations
    lineloads = gather_results()  # read reactions from dummy results and save with coordinates of nodes

    # assign line loads to beams from IN file:
    assign_loads(infile, lineloads)
