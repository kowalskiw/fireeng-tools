# structures-tools
Simple tools for fire structural engineering, which makes the design process easier.

Most of them are intended to be used with SAFIR® - fire structural code by University of Liege, Belgium.
Those scripts are not a part of the software. Nevertheless, some can be used generally to structural fire modelling.

* `safir_tools.py` - pre- and postprocessing of SAFIR® simulations

* `get_in.py` - picking IN files from GiD catalogues and putting them into one directory

* `section_temp.py` - calculating mean temperature from TEM results

* `area2lineload.py` - changing area load to distributed beam load

* `iso2nf.py` - converting ISO heating to natural fire (LOCAFI, HASEMI, CFD), running natural fire simulations for BEAM and SHELL elements

* `uneven_loads.py` - assigning uneven loads to SHELL elements

* `manycfds.py` - calculating thermal response with more than one CFD transfer file

* `part_radf.py` - adjusting FDS transfer files (&RADF product) if FDS calculation has been stopped before T_RADF_END
Link to SAFIR® official website: https://www.uee.uliege.be/cms/c_4016386/en/safir


