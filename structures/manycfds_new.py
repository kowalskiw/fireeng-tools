# napiszę tu jak bym widział strukturę tego skryptu
import copy
import safir_tools
import shutil
import sys
import os


class ManyCfds:
    def __init__(self, config_dir, transfer_dir, mechanical_input_file, safir_exe_path):
        self.config_dir = config_dir
        self.transfer_dir = transfer_dir
        self.mechanical_input_file = mechanical_input_file
        self.safir_exe_path = safir_exe_path
        self.working_dir =  os.path.dirname(mechanical_input_file) 

        self.inFile_backup =  self.get_info_from_infile()
        self.inFile = self.get_info_from_infile()

     
    def main(self):
        self.add_rows()
        self.double_beam_num()
        self.copy_files()
        self.get_all_thermal_infiles()
        self.change_in_for_infiles()
        self.operate_on_cfd()
        self.run_safir_for_all_thermal()       
        

    def get_info_from_infile(self): 
        """
        InFile object is created based on *.in file 
        """
        with open(self.mechanical_input_file, 'r+') as file:
            self.inFile = safir_tools.InFile('dummy', file.readlines())    
        
        return self.inFile

    def add_rows(self): # 
        """ 
            Doubling rows in beamparameters in inFile.file_lines and adding 'cfd_' before beam name
        """
        start = self.inFile.beamparameters['index']+1   #index is the line where beamparameters starts in inFile.file_lines
        end = start + self.inFile.beamparameters['beamnumber']*3
        data_add = self.inFile.file_lines[start:end] 
        for num in range(len(data_add)):
            if data_add[num].endswith(".tem\n"):
                data_add[num] = 'cfd_'+data_add[num]
        self.inFile.file_lines.insert(end, "".join(data_add)) 
        self.end = end # end is the line where beamparameters ends in inFile.file_lines - there's a chance it'll be needed
        

    def double_beam_num(self):
        line_params = self.inFile.file_lines[self.inFile.beamparameters['beamline']].split()   
        line_param_num = line_params[2]
        doubled_param = str(int(line_param_num)*2)
        newbemline = " ".join((line_params[0], line_params[1], doubled_param, "\n")) #1.czy trzeba dodać tab na początku 2. nie mozna dać str.replace.
        self.inFile.file_lines[self.inFile.beamparameters['beamline']] = newbemline  


    def copy_files(self):
        self.copied_mechanical =[]

        for beam in self.inFile.beamparameters['beamtypes']:
            file =beam+'.in'
            modified = 'cfd_'+file
            self.copied_mechanical.append(modified)
            try:
                shutil.copyfile(os.path.join(self.config_dir,file), os.path.join(self.working_dir, modified))    
            except FileNotFoundError as e: 
                print(e)
                sys.exit(1)
        
    def get_all_thermal_infiles(self):
        self.all_thermal_infiles = ['cfd_'+beam+'.in' for beam in self.inFile.beamparameters['beamtypes']]  

    def change_in_for_infiles(self):
        for thermal_infile in self.all_thermal_infiles:
            self.change_in(self.inFile, os.path.join(self.working_dir,thermal_infile), self.inFile.beamparameters['beamtypes'])


        
    def change_in(self, inFile, thermal_in_file, beamtypes, t_end=1200):
        beamtype = inFile.beamparameters['beamtypes'].index(os.path.basename(thermal_in_file)[4:-3])
        # open thermal analysis input file
        with open(thermal_in_file) as file:
            init = file.readlines()

        # save backup of input file
        with open('{}.bak'.format(thermal_in_file), 'w') as file:
            file.writelines(init)

        # make changes
        for no in range(len(init)):
            line = init[no]
            # type of calculation
            if line == 'MAKE.TEM\n':
                init[no] = 'MAKE.TEMCD\n'

                # insert beam type
                [init.insert(no + 1, i) for i in ['BEAM_TYPE {}\n'.format(beamtype), '{}.in\n'.format('dummy')]]

            # change thermal attack functions
            elif line.startswith('   F  ') and 'FISO' in line:  # choose heating boundaries with FISO or FISO0 frontier
                # change FISO0 to FISO
                if 'FISO0' in line:
                    line = 'FISO'.join(line.split('FISO0'))

                # choose function to be changed with
                thermal_attack = 'CFD'

                if 'F20' not in line:
                    init[no] = 'FLUX {}'.format(thermal_attack.join(line[4:].split('FISO')))
                else:
                    init[no] = 'FLUX {}'.format('NO'.join((thermal_attack.join(line[4:].split('FISO'))).split('F20')))
                    init.insert(no + 1, 'NO'.join(line.split('FISO')))

            # change convective heat transfer coefficient of steel to 35 in locafi mode according to EN1991-1-2
            elif 'STEEL' in line:
                init[no + 1] = '{}'.format('35'.join(init[no + 1].split('25')))

            # change T_END
            elif ('TIME' in line) and ('END' not in line):
                try:
                    init[no + 1] = '    '.join([init[no + 1].split()[0], str(t_end), '\n'])
                except IndexError:
                    pass

        # write changed file
        with open(thermal_in_file, 'w') as file:
            file.writelines(init)


    def operate_on_cfd(self):
        for transfer_file in enumerate(os.listdir(self.transfer_dir)):
            
            actual_file = os.path.join(self.transfer_dir,transfer_file[1]) #actual file is a trasfer file on which work is being done
            domain =find_transfer_domain(actual_file) 
            shutil.copyfile(actual_file, os.path.join(self.working_dir,'cfd.txt'))   # zapisz plik transfer_file do folderu, w którym jest mechanical_input_file jako 'cfd.txt'
            self.inFileCopy = copy.deepcopy(self.inFile) 

           

            """
            ADDING ELEMENTS INSIDE DOMAIN
            """
            elements_inside_domain = []
            for element in self.inFile.beams: 

                first_node_id = element[1]
                last_node_id = element[3]
                coordinate_node_first = self.inFile.nodes[first_node_id-1][1:] #id 52 i 53, czy node 0 to środek czy coś takiego?
                coordinate_node_last = self.inFile.nodes[last_node_id-1][1:]    #node id musi byc zmniejszony aby byl spojny z informacjami w beam id

                if ( coordinate_node_first[0]>domain[0] and coordinate_node_last[0] < domain[1] 
                    and coordinate_node_first[1]>domain[2] and coordinate_node_last[1] < domain[3]
                    and coordinate_node_first[2]>domain[4] and coordinate_node_last[2] < domain[5]
                ): 
                    elements_inside_domain.append(element[0])
            
 
            """
            CHANGING BEAM ID AT END OF THE LINE
            """
            lines = 0
            for line in self.inFile.file_lines[self.inFile.beamparameters['elemstart']:]:
                elem_data= line.split()
                if 'ELEM' not in line:
                    break
                if int(elem_data[1]) in elements_inside_domain:
                    actual_line = self.inFile.beamparameters['elemstart']+lines
                    new_beam_number = int(elem_data[-1]) + self.inFile.beamparameters['beamnumber']
                    x = "  "+"\t"+ "\t".join(elem_data[:-1]) + "\t"+str(new_beam_number) + "\n"
                    self.inFile.file_lines[actual_line] = x
                lines+=1



            # zapisz zmodyfikowany plik wejściowy analizy odpowiedzi mechanicznej jako 'dummy.in'
            with open(os.path.join(self.working_dir,"dummy.in"), "a") as f:
                for line in self.inFile.file_lines:
                    f.write(line)

    def run_safir_for_all_thermal(self):
        for file_in in self.all_thermal_infiles:
                file = os.path.join(self.working_dir,file_in)
                safir_tools.run_safir(file, self.safir_exe_path)


def find_transfer_domain(transfer_file):
    #domain = []     # [XA, XB, YA, YB, ZA, ZB]
    with open(transfer_file, 'r+') as file:
        transfer_data_file = file.readlines()
        for num in range(len(transfer_data_file)):
            if 'XYZ_INTENSITIES' in transfer_data_file[num]:
                start = num +1
                break
        for num in range(len(transfer_data_file))[start:]:
            if 'NI' in transfer_data_file[num]:
                end = num -1
                break
        

    all_x, all_y, all_z = [] ,[], []

    for xyzline in transfer_data_file[start:end]:
        x,y,z = xyzline.split()
        all_x.append(x)
        all_y.append(y)
        all_z.append(z)
    domain = [min(all_x), max(all_x),min(all_y),max(all_y),  min(all_z), max(all_z)]
    domain = [float(x) for x in domain]

    # tutaj znajduje granice domeny (box) pliku transferowego
    return domain

if __name__ == '__main__':
    arguments = sys.argv[1:]
    manycfds = ManyCfds(*arguments)
    manycfds.main()
