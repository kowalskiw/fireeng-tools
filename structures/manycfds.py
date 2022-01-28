# napiszę tu jak bym widział strukturę tego skryptu
import copy
import safir_tools
import shutil


# def find_transfer_domain(transfer_file):
#     domain = []     # [XA, XB, YA, YB, ZA, ZB]
#
#     # tutaj znajduje granice domeny (box) pliku transferowego
#
#     return domain
import os.path

#pwd = "D:\ConsultRisk\\fireeng-tools\structures\\" ---- local ----
transfer = "D:\\ConsultRisk\\Warsztaty\\projects\\"
config = "D:\\ConsultRisk\\Warsztaty\\projects\\tem_many\\"
def main(transfer_dir=transfer, config_dir=config, mechanical_input_file = "manycfds_files\\frame.in"):
    #os.chdir(pwd+mechanical_input_file)
    beams_num = 2 # klasa InFile powinna posiadać atrybut: liczbę beamsów - może są ale nie widzę
    # 0. chdir(mechanical_input_file) -> DONE
    # 1. załaduj plik mechanical_input_file (.IN) -frame.in ->DONE
    with open(mechanical_input_file, 'r+') as file:
        inFile = get_info_from_infile() 
        start_file = file.readlines()
        index = [x for x in range(len(start_file)) if 'NODOFBEAM' in start_file[x]][0] #find start of beam informations
        add_rows(start_file, beams_num, index)
        double_beam_num(start_file)
        try:
            copy_files(config_dir, inFile.beamparameters['beamtypes'], 'D:\\ConsultRisk\\Warsztaty\\projects\\new\\')
            print('poszło')
        except:
            "dupa"

def get_info_from_infile(mechanical_input_file = "manycfds_files/frame.in"): 
    """
    InFile object is created based on *.in file 
    """
    with open(mechanical_input_file, 'r+') as file:
        primary = safir_tools.InFile('dummy', file.readlines())    
        print(primary.__dict__['beamparameters']) 
        return primary

def add_rows(file_read, num_of_beams, index):
    """ 
    get data from beams - start and end describes amount of lines that goes to data_add
    in data_add .tem is being found, then prefix is being added 
    amoung of \n has to be checked in new file based on file_read
    """
    start = index+1
    end = start + num_of_beams*3
    data_add = file_read[start:end] 
    for num in range(len(data_add)):
        if data_add[num].endswith(".tem\n"):
            data_add[num] = 'cfd_'+data_add[num]
    file_read.insert(end, "\n".join(data_add)) 
    return file_read

def double_beam_num(file_lines):
    line_params = file_lines[15].split()    #question? - is BEAM can appear on other line than 15?
    line_param_num = line_params[2]
    doubled_param = int(line_param_num)*2
    file_lines[15] = file_lines[15].replace(line_param_num,  str(doubled_param))
    return file_lines       


def copy_files(config_dir, mechanical_input_files, dst_dir):
    for file in mechanical_input_files:
        print(file)
        shutil.copyfile(config_dir+file, dst_dir+'cfd_'+file)   #w folderze config dir znajdują sie pliki .tem
        print(config_dir+file)
        print(dst_dir+'cfd_'+file)




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
    """
        def change_in(thermal_in_file, beamtypes, t_end=1200):

            beamtype = beamtypes.index(os.path.basename(thermal_in_file)[:-3]) + 1

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
    """

    """

    for transfer_file in enumerate(os.scandir(transfer_dir)):
        pass
        # elements_inside_domain = []

        # otwórz plik transfer_file (plik transferowy o nazwie 'cokolwiek_radf_X_Y.txt')

        # znajdź granice domeny obliczeniowej
        # domain = find_transfer_domain(transfer_file)

        # zapisz plik transfer_file do folderu, w którym jest mechanical_input_file jako 'cfd.txt'

        # skopiuj primary na potrzeby tego powtórzenia:
        #   infile = copy.deepcopy(primary)

        # znajdź elementy, które znajdują się w obrębie domeny transferowej (wszystkie element są w infile.beams)
        # for element in infile.beams:
        #       element = [tag_elementu, tag_pierwszego_węzła, tag_środkowego_węzła, tag_końcowego węzła, tag_dodatkowego węzła]
        #   znajdź współrzędne pierwszego i końcowego węzła z infile.nodes:
        #   for node in infile.nodes:
        #       node = [tag_węzła, [x, y, z]]
        #   jeśli element znajduje się w domenie:
        #       elements_inside_domain.append(tag_elementu)

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

        # uruchom obliczenia dla każdego pliku 'cfd_*.in':
        #   safir_tools.run_safir('cfd_profile.in')

    # sprawdź czy liczba plików b_XXXXX_Y.tem jest równa liczbie len(infile.beams) * 2:
    #   jeśli nie - zwróć błąd
    #   jeśli tak - pogratuluj sukcesu, zwróć 0

"""

if __name__ == '__main__':
    main()