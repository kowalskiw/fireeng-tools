from os import chdir, makedirs, system, listdir
import csv


class GetSMVInfo:
    def __init__(self):
        self.chid = 'baletowa_22v6'
        self.path = "/mnt/hgfs/shared_win/0124183148_baletowa_22v1"
        self.end_time = 900

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
                slice_bnds =  self.updating(slice_bnds, mesh, self.choose_bnds(file))

            except ValueError:
                print("I've generated all possible CSV files")
                break
            mesh += 1

        return slice_tab

    def run_fds2ascii(self, msh):
        file_name = 'slice' + str(msh) + '.csv'
        inputab = [self.chid, 2, 10, 'n', str(self.end_time - 10) + ' ' + str(self.end_time),
                   3, 1 + msh, 2 + msh, 3 + msh, file_name]
        input_file = open('bnd_input', 'w')
        [input_file.write(str(i) + '\n') for i in inputab]
        input_file.close()

        system('/home/linux/FDS/FDS6/bin/fds2ascii < bnd_input')

        return file_name

    def choose_bnds(self, file):
        with open(file) as sf_csv:
            sf_file = list(csv.reader(sf_csv))
        dict = {}
        pos = 2
        for i in sf_file[0][2:]:
            tab = []
            [tab.append(float(i[pos])) for i in sf_file[2:]]
            dict.update({i:tab})
            pos += 1

        boundict = {}
        for k in dict.keys():
             boundict.update({k:max(dict[k])})

        return boundict

    def updating(self, slice_bnds, msh, boundict):
        if msh == 1:
            slice_bnds = boundict
        else:
            # breakpoint()
            for k in slice_bnds.keys():
                if slice_bnds[k] < boundict[k]:
                    slice_bnds[k] = boundict[k]

        return slice_bnds


GetSMVInfo().sf_loop()

