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




