# structures-tools
Simple tools for fire structural engineering, which makes the design process easier.

Most of them are intended to be used with SAFIR® - fire structural code by University of Liege, Belgium.
Those scripts are not a part of the software. Nevertheless, some can be used generally to structural fire modelling.

* `area2lineload.py` - numerical conversion of area load to distributed line load on beam (1D) elements (experimental)

* `alotofloacfis.py` - adjusting ignition times of multiple localized fires to tend to given summary HRR curve (experimental)

* `ast2in.py` - transfer of Adiabatic Surface Temperature devices from Fire Dynamics Simulator to SAFIR® beam (1D) elements

* `eliminate.py` - replacing given BEAM element to non-loadbearing using INSULATION material

* `from_gid.py` - picking files of specified extension (-1.T0R by default) from GiD catalogues and putting them together into one directory

* `iso2nf.py` - converting ISO heating to natural fire (LOCAFI, HASEMI, CFD) and then running thermal and structural calculations (supporting BEAM and SHELL elements)

* `manycfds.py` - thermal calculation when more than one CFD transfer file is used (experimental)

* `part_radf.py` - repairing FDS transfer files (&RADF product) when FDS calculation is still in progress or when it has been stopped before T_RADF_END

* `safir_tools.py` - pre- and postprocessing of SAFIR® simulations, moreover some useful functions can be found there

* `section_temp.py` - simple postprocess of 2D thermal results 

* `uneven_loads.py` - assigning uneven loads to SHELL elements


Full documentation will be available soon...

Link to SAFIR® official website: https://www.uee.uliege.be/cms/c_4016386/en/safir


