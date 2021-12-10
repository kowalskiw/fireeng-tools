from os import chdir, makedirs, system, listdir, getcwd
from shutil import rmtree
from PIL import Image
from csv import reader
from numpy import percentile


figure_text = """
\\begin{figure}[htp]
\\begin{center}
\\includegraphics[width=1\\textwidth]{sc1/FIGURE_NAME}
\\end{center}
\\caption{Scenariusz 1 -- Zmiana zasięgu widzialności w FIGURE_TIME sekundzie. }
\\end{figure}
"""


class SliceLvl:
    def __init__(self, ssf_name, times):
        self.times = times
        self.ssf_file_name = ssf_name

    def slice_loop(self):

        slice_tab = ['vSOOT VISIBILITY \n 3 1.8', 'tTEMPERATURE \n 3 1.8', 'tTEMPERATURE \n 3 1.4']
        [(self.set_ini(28), self.create_ssf_file(i), self.run_smokeview()) for i in slice_tab]

    def create_ssf_file(self, slice):
        ssf_file = open(self.ssf_file_name+'.ssf', 'w')
        ssf_file.write('''RENDERDIR
        images
        LOADINIFILE
        '''
         + self.ssf_file_name + '.ini'+
        '''
        SETVIEWPOINT
        auto
        LOADSLICE
        '''
        + slice[1:])
        # + '''
        # LOADINIFILE
        # '''
        # + self.ssf_file_name + '_rep.ini')


        if slice[-1] == '8':
            props = self.times[:2]
        else:
            props = [self.times[2]]
        print(props)
        for i in props:
            ssf_file.write("\n SETTIMEVAL\n" + str(i) + "\nRENDERONCE\n" + slice[0] + str(i) + '\n')
        ssf_file.close()

    def run_smokeview(self):
        system('/home/linux/FDS/FDS6/bin/smokeview -runscript ' + self.ssf_file_name)


    def set_ini(self, marker):
        with open(self.ssf_file_name + '.ini', 'r+') as ini_file:
            ini_tab = list(ini_file.readlines())
            ini_tab[ini_tab.index('TRANSPARENT\n') + 1] = '0 1.000000\n'
            ini_tab[ini_tab.index('COLORBAR\n') + 1] = '12\n'
            # new_ini = open(self.ssf_file_name + '_rep.ini', 'w')
            # new_ini.writelines(ini_tab)
            # new_ini.close()
            ini_file.writelines(ini_tab)
            ini_file.close()





class ScenariosLvl:
    def __init__(self, inpt):
        self.scenarios = inpt[1:]
        self.times = inpt[0]

    def scenario_loop(self):
        for i in self.scenarios:
            chdir(i)
            rmtree('images', ignore_errors=True)
            makedirs('images')
            SliceLvl(i.split('/')[-1][11:], self.times).slice_loop()


class Marker:
    def __init__(self, bounds, pth):
        self.bounds = bounds[:2]
        # print(self.bounds)
        self.path = pth
        self.crit = bounds[2]
        # print(self.crit)

    def run4all(self):
        # not universal function

        imgtab = listdir(self.path)
        # print(self.path, imgtab)
        if self.crit == 10:
            imgtab = imgtab[3:]
        elif self.crit == 57.3:
            imgtab = [imgtab[0], imgtab[1]]
        elif self.crit == 95:
            imgtab = [imgtab[2]]
            # print(imgtab)

        for i in imgtab:
            self.change_pix(self.path + "/" + i)

    def create_mtx(self, flip=0):
        my_pal = []
        for i in range(256):
            my_pal.append((255, i, 0))
        for i in range(256):
            my_pal.append((255 - i, 255, 0))
        for i in range(256):
            my_pal.append((0, 255, i))
        for i in range(256):
            my_pal.append((0, 255 - i, 255))

        if flip == 1:
            my_pal.reverse()

        return my_pal

    def change_pix(self, img_path):
        pixel_no = int(1024 * ((self.crit - self.bounds[0]) / (self.bounds[1] - self.bounds[0])))
        print(self.bounds)
        print(img_path)
        img = Image.open(img_path)
        data = list(img.getdata())
        flp = 0
        if img_path.split("/")[-1][0] == 't':
            print('flipped')
            flp = 1

        for i in self.create_mtx(flip=flp)[pixel_no - 20: pixel_no + 20]:
            print(data.count(i))
            for j in range(data.count(i)):
                data[data.index(i)] = (0, 0, 0)

        img.putdata(data)
        img.save(img_path, "PNG")

        return True


class GetSMVInfo:
    def __init__(self, path):
        self.chid = '_'.join(path.split('/')[-1].split('_')[1:])
        self.path = path
        self.end_time = 1000
        chdir(self.path)

    def sf_loop(self):
        slice_tab = []
        for i in listdir(self.path):
            if i[-3:] == ".sf":
                slice_tab.append(i)

        mesh = 1
        slice_bnds = {}
        while True:
            try:
                file = self.run_fds2ascii(slice_tab.index(self.chid + '_000' + str(mesh) + "_01.sf"))
                slice_bnds = self.updating(slice_bnds, mesh, self.choose_bnds(file))

            except ValueError:
                print("ValueError or I've generated all possible CSV files")
                break
            mesh += 1

        return slice_bnds

    '''finally inputab should be normalized, i.e. slices 1, 2 and 3 are VIS1.4, TEMP1.4, TEMP1.8
            we should implement slices in correct order while creating .fds file'''

    def run_fds2ascii(self, msh):
        file_name = 'slice' + str(msh) + '.csv'
        inputab = [self.chid, 2, 1, 'n', str(self.end_time - 1) + ' ' + str(self.end_time),
                   3, 1 + msh, 2 + msh, 5 + msh, file_name]
        input_file = open('bnd_input', 'w')
        [input_file.write(str(i) + '\n') for i in inputab]
        input_file.close()

        system('/home/linux/FDS/FDS6/bin/fds2ascii < bnd_input')

        return file_name

    def choose_bnds(self, file):
        with open(file) as sf_csv:
            sf_file = list(reader(sf_csv))
        dict = {}
        pos = 2
        for i in sf_file[0][2:]:
            tab = []
            [tab.append(float(i[pos])) for i in sf_file[2:]]
            dict.update({(i + str(pos)): tab})
            pos += 1

        boundict = {}
        for k in dict.keys():
             boundict.update({k: percentile(dict[k], 98)})

        return boundict

    def updating(self, slice_bnds, msh, boundict):
        if msh == 1:
            slice_bnds = boundict
        else:
            for k in slice_bnds.keys():
                if slice_bnds[k] < boundict[k]:
                    slice_bnds[k] = boundict[k]

        return slice_bnds

    def convertuple(self):
        critab = []
        for k, v in self.sf_loop().items():
            if k == ' TEMPERATURE4':
                critab.append((20, v, 57.3))
            elif k == ' TEMPERATURE3':
                critab.append((20, v, 95))
            elif k == ' SOOT VISIBILITY2':
                critab.append((0, v, 10))
            elif k == ' VELOCITY':
                critab.append((0, v, 5))

        return critab


if __name__ == '__main__':
    results_paths = ["/mnt/hgfs/shared_win/0218125641_baletowa_atrium_v1"] # , "/mnt/hgfs/shared_win/0131184821_g_lop_sym4"]

    ScenariosLvl([[50, 250, 900], *results_paths]).scenario_loop()

    # for i in results_paths:
    #     crit_tab = GetSMVInfo(i).convertuple()
    #     for j in crit_tab:
    #         print('marking process has been started')
    #         Marker(j, i + '/images').run4all()
