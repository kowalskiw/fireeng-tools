import safir_tools as st
from sys import argv


class Eliminator:
    def __init__(self, infilepath):
        self.infile = st.read_in(infilepath)

    def check(self, what):
        objects = [[self.infile.materials, 'INSULATION'], [self.infile.beamtypes, 'ins_foo.tem']]
        for i in objects[what][0]:
            if i[0] == objects[what][1]:
                return False
        return True

    def eliminate(self, to_be_eliminated):
        change = False
        for i, line in enumerate(self.infile.file_lines):
            if 'RELAX' in line or 'PRECISION' in line:
                change = False
            elif all([change, 'ELEM' in line]):
                spltd = line.split()
                if spltd[1] in to_be_eliminated:
                    self.infile.file_lines[i] = '\t'.join(spltd[:-1]) + '\t' + str(len(self.infile.beamtypes)) + '\n'

            elif 'NMAT' in line and self.check(0):
                self.infile.file_lines[i] = f'\tNMAT\t{str(int(line.split()[-1]) + 1)}\n'
            elif all(['BEAM' in line, 'NODOF' not in line, 'S' not in line, self.check(1)]):
                spltd = line.split()
                self.infile.file_lines[i] = '\t'.join(spltd[:-1]) + '\t' + str(int(spltd[-1]) + 1) + '\n'
            elif all(['END_TRANS' in line, 'ELEM' in self.infile.file_lines[i + 1]]):
                if self.check(1):
                    self.infile.file_lines.insert(i + 1,
                                                  f'ins_foo.tem\nTRANSLATE\t1\t{len(self.infile.materials) + 1}\nEND_TRANS\n')
                    self.infile.beamtypes.append(['ins_foo.tem', [len(self.infile.materials) + 1]])
                change = True
            elif 'TIME' in line and self.check(0):
                self.infile.file_lines.insert(i, 'INSULATION\n')
                self.infile.materials.append(['INSULATION', []])
                break

        self.save_foo_tem()
        self.infile.save_line(f'{self.infile.chid}_el.in')

    def save_foo_tem(self):
        geom = ['\tNFIBERBEAM\t4\n',
                '\tFIBERS\n',
                '\tNODELINE\t0\t0\n',
                '\tYC_ZC\t0\t0\n',
                '-0.001\t-0.001\t0\t1\t0\n',
                '0.001\t-0.001\t0\t1\t0\n',
                '0.001\t0.001\t0\t1\t0\n',
                '-0.001\t0.001\t0\t1\t0\n',
                '\tw\n',
                '  -0.000001   -0.000001   0.000000\n',
                '  0.000001   -0.000001   0.000000\n',
                '  0.000001   0.000001   0.000000\n',
                '  -0.000001   0.000001   0.000000\n',
                'According to the principle of virtual works,\n',
                'GJ=  1,0\n'
                '\tHOT\n\n']
        steps = []
        for t in range(60, int(self.infile.t_end) + 1, 60):
            steps.extend([f'TIME=     {t}.0000 SECONDS   OR   {int(t / 60)} MIN.  {int(t % 60)} SEC.\n',
                          '===========================================\n',
                          '1   20.0\n',
                          '2   20.0\n',
                          '3   20.0\n',
                          '4   20.0\n\n'])

        with open('ins_foo.tem', 'w') as f:
            f.writelines(geom + steps)


if __name__ == '__main__':
    e = Eliminator(argv[1])
    e.eliminate(argv[2:])
