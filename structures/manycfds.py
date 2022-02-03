# napiszę tu jak bym widział strukturę tego skryptu
import copy
import safir_tools
import shutil
import sys
import os

 
def main(transfer_dir, config_dir, mechanical_input_file):
    working_dir = os.path.dirname(mechanical_input_file)+'//' 
    #os.chdir(pwd+mechanical_input_file) # folder z mechanical input file
    # 0. chdir(mechanical_input_file) -> DONE
    # 1. załaduj plik mechanical_input_file (.IN) -frame.in ->DONE
    with open(mechanical_input_file, 'r+') as file:

        inFile_backup =  get_info_from_infile(mechanical_input_file)
        inFile = get_info_from_infile(mechanical_input_file)
        
        end = add_rows(inFile.file_lines, inFile.beamparameters['beamnumber'], inFile.beamparameters['index'])
        double_beam_num(inFile.file_lines, inFile)
      
        try:
            copied = copy_files(config_dir, inFile.beamparameters['beamtypes'], working_dir)  
            print('File copied')
        except:
            print("Something went wrong during copying")
        
        all_thermal_infiles = ['cfd_'+beam+'.in' for beam in inFile.beamparameters['beamtypes']]  
        for thermal_infile in all_thermal_infiles:
            change_in(inFile, working_dir+thermal_infile, inFile.beamparameters['beamtypes'])
       
        operate_on_cfd(inFile=inFile, transfer_dir = transfer_dir, working_dir = working_dir)

        for file_in in all_thermal_infiles:
            file =working_dir+file_in
            safir_tools.run_safir(file)
        
       
        

def get_info_from_infile(mechanical_input_file): 
    """
    InFile object is created based on *.in file 
    """
    with open(mechanical_input_file, 'r+') as file:
        primary = safir_tools.InFile('dummy', file.readlines())    
        return primary

def add_rows(file_lines, num_of_beams, index): # zmienić na operowanie na inFile object
    """ 
    get data from beams - start and end describes amount of lines that goes to data_add
    in data_add .tem is being found, then prefix is being added 
    amoung of \n has to be checked in new file based on file_lines
    """
    start = index+1
    end = start + num_of_beams*3
    data_add = file_lines[start:end] 
    for num in range(len(data_add)):
        if data_add[num].endswith(".tem\n"):
            data_add[num] = 'cfd_'+data_add[num]
    file_lines.insert(end, "".join(data_add)) 
    return end

def double_beam_num(file_lines, inFile):
    beamline = file_lines[inFile.beamparameters['beamline']] #line where BEAM appears
    
    line_params = beamline.split()   
    line_param_num = line_params[2]
    doubled_param = str(int(line_param_num)*2)
    newbemline = " ".join((line_params[0], line_params[1], doubled_param, "\n")) #1.czy trzeba dodać tab na początku 2. nie mozna dać str.replace.
    inFile.file_lines[inFile.beamparameters['beamline']] = newbemline
    return file_lines       


def copy_files(config_dir, mechanical_input_files, dst_dir):
    copied_mechanical =[]
    for file in mechanical_input_files:
        file =file+'.in'
        modified = 'cfd_'+file
        copied_mechanical.append(modified)
        shutil.copyfile(config_dir+file, dst_dir+ modified)   #w folderze config dir znajdują sie pliki .tem
    return copied_mechanical 



    # 2. zdubluj wszystkie wpisy definiujące rodzaje przekroi w primary.file_lines, dopisując przedrostek 'cfd_' -> DONE
    # z czegoś takiego:
    #====================
    #     NODOFBEAM
    #    ipe600.tem
    #     TRANSLATE    1    1
    #     END_TRANS
    #    profil.tem
    #     TRANSLATE    2    1   2
    #     END_TRANS
    #====================
    # na coś takiego:
    #====================
    #     NODOFBEAM
    #    ipe600.tem
    #     TRANSLATE    1    1
    #     END_TRANS
    #    profil.tem
    #     TRANSLATE    2    1   2
    #     END_TRANS
    #    cfd_ipe600.tem
    #     TRANSLATE    1    1
    #     END_TRANS
    #    cfd_profil.tem
    #     TRANSLATE    2    1   2
    #     END_TRANS
    #====================

    # 3. zapisz wszystkie rodzaje przekrojów ('*.tem') do listy beamtypes = ['profil1.tem', 'profil2.tem'...] -> DONE


    # 4. następnie podwój tę liczbę i nadpisz w primary.file_lines -> DONE
    # z czegoś takiego:
    #====================
    #   BEAM  18672    17
    #====================
    # na coś takiego:
    #====================
    #   BEAM  18672    34
    #====================


    # 5. skopiuj z lokalizacji config_dir pliki wejściowe analizy odpowiedzi termicznej '*.in'
        # (oddziaływanie termiczne tylko FISO)

    # 6. dodaj przedrostek 'cfd_' do nazw tych plików (modyfikacja nazw)

    # 7. zmodyfikuj pliki 'cfd_*.in' za pomocą funkcji change_in (FISO -> CFD)
    
def change_in(inFile, thermal_in_file, beamtypes, t_end=1200):
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


def operate_on_cfd(inFile, transfer_dir, working_dir):
    for transfer_file in enumerate(os.listdir(transfer_dir)):
        
        actual_file = transfer_dir+transfer_file[1]
        domain =find_transfer_domain(actual_file) # znajdź granice domeny obliczeniowej   # domain = find_transfer_domain(transfer_file)
        shutil.copyfile(actual_file, working_dir+'cfd.txt')   # zapisz plik transfer_file do folderu, w którym jest mechanical_input_file jako 'cfd.txt'
        inFileCopy = copy.deepcopy(inFile)

        elements_inside_domain = []
        with open(actual_file) as file:# otwórz plik transfer_file (plik transferowy o nazwie 'cokolwiek_radf_X_Y.txt')
            file_lines = file.readlines() 
            
        # zapisz plik transfer_file do folderu, w którym jest mechanical_input_file jako 'cfd.txt'

        # skopiuj primary na potrzeby tego powtórzenia:
        #   infile = copy.deepcopy(primary)
        #[min_x, max_x, min_y, max_y,  min_z, max_z]
        domain = [float(x) for x in domain]

        # znajdź elementy, które znajdują się w obrębie domeny transferowej (wszystkie element są w infile.beams)
        # for element in infile.beams:
        element = inFile.beams[0]
        first_node_id = element[1]
        last_node_id = element[3]
        coordinate_node_first = (first_node_id, inFile.nodes[first_node_id]) #id 52 i 53, czy node 0 to środek czy coś takiego?
        coordinate_node_last = (last_node_id, inFile.nodes[last_node_id]) 

                #          [1,          __52__,                     164,                __53__,                    326,         1]
        #       element = [tag_elementu, tag_pierwszego_węzła, tag_środkowego_węzła, tag_końcowego węzła, tag_dodatkowego węzła]
        #   znajdź współrzędne pierwszego i końcowego węzła z infile.nodes:
        #domain_names = ['min_x', 'max_x', 'min_y', 'max_y',  'min_z', 'max_z']
        #coordinate_names = ['x','y','z']


        """
        FUNKCJA DODAJĄCA ELEMENTY ZNAJDUJĄCE SIĘ W DOMENIE
        """
        for element in inFile.beams[:10]:
            first_node_id = element[1]
            last_node_id = element[3]
            coordinate_node_first = inFile.nodes[first_node_id][1:] #id 52 i 53, czy node 0 to środek czy coś takiego?
            coordinate_node_last = inFile.nodes[last_node_id][1:]
            #print(coordinate_node_first, coordinate_node_last)
            #print(domain)
            if ( coordinate_node_first[0]>domain[0] and coordinate_node_last[0] < domain[1] 
                and coordinate_node_first[1]>domain[2] and coordinate_node_last[1] < domain[3]
                and coordinate_node_first[2]>domain[4] and coordinate_node_last[2] < domain[5]
            ): elements_inside_domain.append(element[0])
        
        #print(elements_inside_domain)
        # przykładowa lista, poprzednia pusta
        
        #   for node in infile.nodes:
        #       node = [tag_węzła, [x, y, z]]
        #   jeśli element znajduje się w domenie:
        #       elements_inside_domain.append(tag_elementu)
        
       
        lines = 0
        """
        FUNKCJA ZMIENIAJĄCA id przekroju na koncu wiersza
        """
        for line in inFile.file_lines[inFile.beamparameters['elemstart']:]:
            elem_data= line.split()
            #print(elem_data)
            
                #inFile.file_lines[actual_line] = " ".join([str(x) for x in elem_data[:-1]], str(elem_data[-1]+len(inFile.beamparameters['beamtypes'])/2))
            if 'ELEM' not in line:
                break
            if int(elem_data[1]) in elements_inside_domain:
                actual_line = inFile.beamparameters['elemstart']+lines
                new_beam_number = int(elem_data[-1]) + inFile.beamparameters['beamnumber']
                x = "  "+"\t"+ "\t".join(elem_data[:-1]) + "\t"+str(new_beam_number) + "\n"
                inFile.file_lines[actual_line] = x
            lines+=1

        # for line in inFile.file_lines[350:370]:
        #     print(line)
        
        # zmień rodzaj przekroju dla elementów znajdujących się w domenie transferowej w infile.file_lines z x na x+len(beamtypes)/2:
        #                tag    node1   node2    node3   node4  rodzaj_przekroju
        #         ELEM   149    8654    17876    8561    36548    1
        #
        # z czegoś takiego:
        #=========================================================
        #         ELEM   1    8654    17876    8561    36548    1
        #         ELEM   2    8561    17877    8489    36549    2
        #=========================================================
        # na coś takiego (przy nbeamtype==6):
        # =========================================================
        #         ELEM   1    8654    17876    8561    36548    7
        #         ELEM   2    8561    17877    8489    36549    8
        # =========================================================

        # zapisz zmodyfikowany plik wejściowy analizy odpowiedzi mechanicznej jako 'dummy.in'
        with open(working_dir+"dummy.in", "a") as f:
            for line in inFile.file_lines:
                f.write(line)
      
        # uruchom obliczenia dla każdego pliku 'cfd_*.in':
        #   safir_tools.run_safir('cfd_profile.in')


    # sprawdź czy liczba plików b_XXXXX_Y.tem jest równa liczbie len(infile.beams) * 2:
    #   jeśli nie - zwróć błąd
    #   jeśli tak - pogratuluj sukcesu, zwróć 0

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
        #print(start, end) # czy bedziemy operować potem na liniach XYZ INTENSITIES

    all_x, all_y, all_z = [] ,[], []

    for xyzline in transfer_data_file[start:end]:
        x,y,z = xyzline.split()
        all_x.append(x)
        all_y.append(y)
        all_z.append(z)
    domain = [min(all_x), max(all_x),min(all_y),max(all_y),  min(all_z), max(all_z)]
    # tutaj znajduje granice domeny (box) pliku transferowego
    return domain

if __name__ == '__main__':
    arguments = sys.argv[1:]
    main(*arguments)
