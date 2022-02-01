import dxfgrabber as dxf
from sys import argv
import numpy as np
from math import ceil
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import argparse as ar

'''VERSION 0.1.0'''

'''Script genarates locafi_script.txt file which contains set of template fires
burned one by one to achieve certain t-squared curve

You have to specify template fire [TXT], possible fire locations (centeres of fire base circles) [DXF]
and fire growth factor [W/s^2] you tend to'''

'''config.txt can be specified to achieve better fire curve adjustment. There are two binary options to be specified.
[yes/1/true/y] stands for True and [no/0/false/n] stands for False. One option takes small float value.
        
        
        time_step -> what time step (int) [s] do you want to use in calculations (default: 1)
        alpha -> fire growth factor of lim fire curve (no default)
        optimize  -> do you want to use optimization function (default: false)(options: iter/coeff)
            #for iterative optimization#
                int_time -> initial time step [s] (default:10)
                bottom -> relative bottom tolerance (default: 0.05)
                upper -> relative upper tolerance (default: 0.1)
                optim_step -> optimization time_step (default: global time_step)
            
            #for optimization with precision coefficient#
                relative -> do you want to optimize with relative error (no default)(suggestion: 0)
                precision -> what precision factor do you want to use (no default)(suggestion: 0.001)
'''


def basic_locafi(template_pth):
    """read LOCAFI fire file;
        return [end time [int], z_ceiling [int], lines of diameter table[list(string)], lines of RHR table[list(string)],
        origin point [list(float)], maximum RHR [float]"""
    origin = []
    z_ceiling = 0
    read = [False, False]
    diameter = ['DIAMETER\n\n', 'END_DIAM\n\n']
    rhr = ['RHR\n\n', 'END_RHR\n\n']

    with open(template_pth) as file:
        template = file.readlines()

    for l in template:
        if 'FIRE_POS' in l:
            origin = [float(i) for i in l.split()[1:]]
        elif 'Z_CEILING' in l:
            z_ceiling = float(l.split()[-1])
        elif 'DIAMETER' in l:
            read[0] = True
        elif 'END_DIAM' in l:
            read[0] = False
        elif 'RHR' in l:
            read[1] = True
        elif 'END_RHR' in l:
            read[1] = False

        elif read[0]:
            diameter.insert(-1, l)

        elif read[1]:
            rhr.insert(-1, l)

    q_tab = []
    for i in rhr[1:-1]:
        try:
            q_tab.append(float(i.split()[-1]))
        except IndexError:
            pass

    print('[OK] locafi template imported')

    for i in reversed(diameter):
        try:
            tend = int(i.split()[0])
            break
        except (IndexError, ValueError):
            pass

    return tend, z_ceiling, diameter, rhr, origin, max(*q_tab)


def locations_dxf(dxf_with_points):
    """read possible fire location points from DXF file"""
    coord_list = []

    dxffile = dxf.readfile(dxf_with_points)

    for ent in dxffile.entities:
        if ent.dxftype == 'POINT':
            coord_list.append(list(ent.point))

    print('[OK] fires coordinates read')

    return coord_list


def lcf2array(tab, one_d=False):
    """convert string table from LOCAFI fire file to the list(float)"""
    new = []
    for l in tab:
        ls = l.split()
        if len(ls) > 1:
            new.append([float(ls[0]), float(ls[1])])

    if one_d:
        newer = []
        for t in range(int(new[-1][0]) + 1):
            newer.append(np.interp(t, *zip(*new)))
        return newer

    else:
        return new


def array2lcf(tab, type: str):
    """convert list(float) to the string table from LOCAFI fire file"""
    if type.lower() in ['rhr', 'hrr', 'q', 'q\'']:
        new = ['RHR\n', 'END_RHR\n']
    elif type.lower() in ['diam', 'diameter', 'd']:
        new = ['DIAMETER\n', 'END_DIAM\n']
    else:
        raise ValueError(f'{type} "type" variable not valid')

    for row in tab:
        new.append('\t{} {}'.format(*row))

    return new


class TendToFireWithLOCAFI:
    def __init__(self, ins, time_step=1):
        self.config = ins
        self.t_end, self.z_ceiling, self.diameter, self.rhr, self.origin, self.q_max = basic_locafi(ins.fire)
        self.possible_locations = self.sort_coords()
        self.n_of_fires = []
        self.estimated_fc = np.array([0.0] * (self.t_end + 1))
        self.lim_fc = self.make_lim_fc()
        self.one_fc = lcf2array(self.rhr, one_d=True)
        self.time_step = time_step

    '''return fire curve to be tend to'''

    def make_lim_fc(self):
        return np.array([])

    '''sort coordinates of possible fire locations with distance to fire origin'''

    def sort_coords(self):
        norigin = np.array(self.origin)
        sortd = []
        latest = 1e90
        raw = locations_dxf(self.config.localization)
        for c in raw:
            nc = np.array(c)
            dist = np.sqrt(np.sum((norigin - nc) ** 2, axis=0))
            if dist < latest:
                latest = dist
                sortd.insert(0, c)
            else:
                sortd.append(c)

        return sortd

    '''shift the beginning of RHR or diameter string table to the starttime'''

    def actual(self, tab, starttime):
        changed = [tab[0], '\t0.0 0.0']  # add RHR or DIAMETER placeholder and (0,0) startpoint

        for i in list(tab[1:-1]):  # iterate over single-fire RHR/diameter table records
            itab = i.split()
            try:
                if float(itab[0]) + starttime > self.t_end:  # check if next value is  greater than end time
                    last = changed[-1].split()
                    t_step = float(itab[0]) - float(last[0])
                    v_step = float(itab[1]) - float(last[1])
                    if t_step <= 0:  # check if this fire will burn for at least self.time_step
                        v_end = 0.0
                    else:
                        v_end = float(last[1]) + (self.t_end - float(last[0])) / t_step * v_step  # interpolate

                    # add the last value
                    changed.append(f'\t{self.t_end} {v_end}\n')
                    break

                else:
                    # add the middle value
                    changed.append(f'\t{float(itab[0]) + starttime} {itab[1]}\n')

            except IndexError:
                changed.append('\n')

        changed.append(tab[-1])  # add END_RHR or END_DIAM placeholder

        return changed

    '''create new locafi_scripted.txt LOCAFI fire file with ignition data from self.n_of_fires'''

    def make_lcfs(self):
        fires_coords = self.sort_coords()
        self.t_end = len(self.n_of_fires)

        new_lcf = ['NFIRE {}\n\n'.format(self.n_of_fires[-1])]

        loc = 0
        for t in range(1, self.t_end):
            # check how many fires should be added in time step of t
            for i in range(self.n_of_fires[t] - self.n_of_fires[t - 1]):
                # add fire at the nearest not-burning spot
                try:
                    new_lcf.extend([f'FIRE_POS  {" ".join([str(i) for i in fires_coords[loc]])}\n'
                                    f'Z_CEILING  {self.z_ceiling}\n'
                                    f'PLUME_TYPE CONIC\n',
                                    *self.actual(self.diameter, t - 1),
                                    *self.actual(self.rhr, t - 1)])
                except IndexError:
                    raise ValueError('Number of fires locations is lower than required. Check DXF file and fire growth'
                                     'factor [W/s^2]')
                loc += 1

        with open('locafi_script.txt', 'w') as file:
            file.writelines(new_lcf)

        print('[OK] "locafi_script.txt" written')

    '''make np.array with estimated fire curve (summary of multiple single fires RHR) based on self.n_of_fires'''

    def estimate(self):
        self.estimated_fc.fill(0)
        actual = 0
        t = 0
        for i in self.n_of_fires[1:]:
            t += 1
            new = i - actual
            if new > 0:
                for j in range(new):
                    actual += 1
                    self.estimated_fc = np.add(self.estimated_fc, np.array([0.0] * t + self.one_fc)[:self.t_end + 1])

    '''make charts of estimated fire curve, lim fire curve and relative and absolute error'''

    def rhr_charts(self):
        self.estimate()

        # Create 2x2 sub plots
        gs = gridspec.GridSpec(3, 2)
        fig = plt.figure()
        fig.suptitle('travelling fire estimation')

        # absolute error chart
        err = fig.add_subplot(gs[2, 0])  # row 0, col 0
        err.plot(range(self.time_step, self.t_end),
                 [self.estimated_fc[t] - self.lim_fc[t] for t in range(self.time_step, self.t_end)])
        err.set(ylabel='RHR error, [W]', xlabel='Time, [s]')

        # relative error chart
        rel_err = fig.add_subplot(gs[2, 1])  # row 0, col 1
        rel_err.plot(range(self.time_step, self.t_end),
                     [(self.estimated_fc[t] - self.lim_fc[t]) / self.lim_fc[t] for t in
                      range(self.time_step, self.t_end)])
        rel_err.set(ylabel='Relative RHR error, [-]', xlabel='Time, [s]')

        # estimated and lim fire curves chart
        fc = fig.add_subplot(gs[0, :])  # row 2, span all columns
        fc.plot(0.95 * self.lim_fc, color='#c30404ff', linestyle='--')
        glf, = fc.plot(1.05 * self.lim_fc, color='#c30404ff', linestyle='--', label='Lim Fire Curve +/-5%')
        lf, = fc.plot(self.lim_fc, color='#c30404ff', linestyle='dotted', label='Lim Fire Curve')
        ef, = fc.plot(self.estimated_fc, label='Estimated Fire Curve', color='#0080d7')
        fc.legend(handles=[lf, ef, glf])
        fc.set(ylabel='Rate of Heat Release, [W]', xlabel='Time, [s]')

        # number of fires
        nf = fig.add_subplot(gs[1, :])  # row 1, span all columns
        nf.plot(self.n_of_fires, color='red', linestyle='-')
        nf.set(ylabel='Number of fires burning, [-]', xlabel='Time, [s]')

        [i.grid(True) for i in [err, rel_err, fc, nf]]

        # plt.show()
        plt.savefig('locafi_script.png')
        print('[OK] figure saved')

    '''trying to achieve better correlation with lim fire curve by modifying the analytical equation - poor method'''

    def optimize_corr(self, precision=0.001, relative=True):
        delta_mean = [1]
        corr = 0
        stop = False
        multi = 1
        while abs(delta_mean[-1]) > precision and not stop:
            print(f'delta_mean: {delta_mean[-1]}', end='\r')
            if delta_mean[-1] > 0:  # rhr too high
                corr -= multi * precision
            else:  # rhr too low
                corr += multi * precision
            self.plateau_method(corrector=corr)
            self.estimate()
            if relative:
                delta_mean.append(sum([(self.estimated_fc[t] - self.lim_fc[t]) / self.lim_fc[t]
                                       for t in range(self.time_step, self.t_end)]) / (self.t_end - 1))
            else:
                delta_mean.append(sum([self.estimated_fc[t] - self.lim_fc[t]
                                       for t in range(self.time_step, self.t_end)]) / (self.t_end - 1))
            if True:
                multi *= 2

            try:
                if delta_mean[-1] * delta_mean[-2] < 0:
                    if multi >= -1:
                        multi /= 2
                else:
                    pass

                if multi < 1:
                    break

                c = 0
                for t in range(-1, -21, -1):
                    if delta_mean[t] * delta_mean[t - 1] < 0:
                        c += 1
                    if c == 20:
                        stop = True
            except IndexError:
                pass
        print('[OK] optimization with modifier finished')

    '''trying to achieve better correlation with lim fire curve by iterating over generated fire curve and modifying 
    ignition time'''

    def optimize_iter(self, bottom: float = -0.03, top: float = 0.15, initial_time: int = 10, optim_step: int = 1):
        time_step = optim_step if optim_step else self.time_step
        np_of_fires = np.array(self.n_of_fires)
        self.estimate()
        t = initial_time
        iter_count = [t, 0]

        def check_if_acending(one_d_tab):
            prev = 0
            for i in one_d_tab:
                if i - prev < 0:
                    return False
                else:
                    prev = i
            return True

        def find_ignition(np_of_f, n):
            return list(np_of_f).index(n)

        def modify(actual_time, back=None):
            print('comeback ', back)
            newt = actual_time + back * time_step
            if 0 > newt:
                do_move = False  # remove fire
                newt = 0
            elif newt > self.t_end:
                do_move = False  # remove fire
                newt = self.t_end
            else:
                do_move = True  # move fire

            if back > 0:  # rhr too high - move forward or remove if moving is not possible
                if not do_move:
                    np_of_fires[newt:] -= 1
                    print('removed one fire at {} s'.format(newt))
                else:
                    iter_count2 = 0
                    while True:
                        t_from = find_ignition(np_of_fires, np_of_fires[actual_time] - iter_count2)  # find the ignition time
                        t_to = t_from + time_step  # one time_step forward

                        # check if you can move one fire one time_step forward:
                        for i in range(t_from, t_to):  # try to move forward
                            np_of_fires[i] -= 1

                        if not check_if_acending(np_of_fires):  # check if number of fires list is not descending
                            for i in range(t_to, t_from):   # if so, undo the changes...
                                np_of_fires[i] += 1
                            iter_count2 += 1   # ... and try to move previous fire

                        else:
                            print('one fire moved forward from {} s to {} s'.format(t_from, t_to))
                            break

                        if t_from < time_step or t_to < time_step or t_from == t_to:
                            print('[WARNING] I can\'t move any fire to make this time step in error ranges')
                            return back, newt

                    newt = t_to

            elif back < 0:  # rhr too low - move backwards
                iter_count2 = 0
                t_to = 1e9
                while True:
                    if not do_move:
                        np_of_fires[actual_time-1:] += 1
                        print('added one fire at {} s'.format(actual_time-1))
                        return actual_time-1

                    if t_to <= initial_time:
                        try:
                            t_from = find_ignition(np_of_fires, np_of_fires[actual_time]+1)  # find the ignition time
                        except ValueError:  # can't move a fire, need to add one
                            do_move = False
                            continue
                    else:
                        t_from = find_ignition(np_of_fires, np_of_fires[actual_time])  # find the ignition time

                    t_to = t_from - time_step - iter_count2  # add the fire one step before actual time
                    if t_to <= initial_time:
                        continue
                    iter_count2 += 1
                    # # check if you can move one fire one time_step forward:
                    # for i in range(t_from, t_to):  # try to move forward
                    #     np_of_fires[i] -= 1
                    #
                    # if not check_if_acending(np_of_fires):  # check if number of fires list is not descending
                    #     for i in range(t_to, t_from):   # if so, undo the changes...
                    #         np_of_fires[i] += 1
                    #     iter_count2 += 1   # ... and try to move previous fire

                    # try to move the fire
                    print(t_to, t_from)
                    for i in range(t_to, t_from):
                        np_of_fires[i] += 1

                    print('one fire moved backwards from {} s to {} s'.format(t_from, t_to))
                    return t_to

                    # if t_from < time_step or t_to < time_step or t_from == t_to:
                    #     print('[WARNING] I can\'t move any fire to make this time step in error ranges')
                    #     return back, newt

            # else:
            #
            #     # check if you can move a fire in newt timestep:
            #     t_from = newt
            #     t_to = actual_time
            #     while True:
            #         for i in range(t_to, t_from):
            #             np_of_fires[i] += 1
            #
            #         if not check_if_acending(np_of_fires):
            #             for i in range(t_to, t_from):
            #                 np_of_fires[i] -= 1
            #         else:
            #             print('one fire moved from {} s to {} s'.format(t_from, t_to))
            #             break
            #
            #         t_from -= time_step
            #         t_to -= time_step
            #
            #         if t_from < time_step or t_to < time_step or t_from == t_to:
            #             return back, newt
            #
            #         # if np_of_fires[t_from] >= np_of_fires[t_from-1]:
            #         #     for i in range(t_to, t_from):
            #         #         np_of_fires[i] += 1
            #         #     print('one fire moved from {} s to {} s'.format(t_from, t_to))
            #         #     break
            #         #
            #         # t_from -= time_step
            #         # t_to -= time_step
            #         #
            #         # if t_from < time_step or t_to < time_step or t_from == t_to:
            #         #     return back, newt
            #
            #     newt = t_to

            else:
                raise ValueError('"comeback" parameter cannot have value "0"')

            return newt

        while True:
            t = time_step if t < time_step else t
            delta_rhr = (self.estimated_fc[t] - self.lim_fc[t]) / self.lim_fc[t]
            print(f'\n{t}/{self.t_end}')
            print(self.lim_fc[t], self.estimated_fc[t])
            print(f'RHR difference: {delta_rhr}')

            if delta_rhr < bottom:  # rhr too low
                t = modify(t, back=-1)
                self.n_of_fires = list(np_of_fires)
                print(np_of_fires)
                self.estimate()

            elif delta_rhr > top:  # rhr too high
                t = modify(t, back=1)  # change estimated_fc
                self.n_of_fires = list(np_of_fires)
                print(np_of_fires)
                self.estimate()

            else:  # rhr ok
                print(f'[OK] Converged at {t} s')
                t += time_step
                iter_count[1] = 0
                if t >= self.t_end:
                    break

            if iter_count[0] == t:
                iter_count[1] += 1

            if iter_count[1] >= 10:
                print(f'[ERROR] No convergence after 10 iterations at {t} s')
                exit(-1)


class TendToTSquared(TendToFireWithLOCAFI):
    def __init__(self, ins, time_step=1):
        self.alpha = ins.alpha  # [W/s^2]
        super().__init__(ins, time_step)
        self.n_of_fires = self.plateau_method()

    '''return t-squared fire curve to be tend to'''

    def make_lim_fc(self):
        return np.array([self.alpha * t ** 2 for t in range(self.t_end + 1)])

    '''find how many single_fc fires needs to be burning to achive lim_fc
        assuming steady state fire with Q(t) = Q_max'''

    def plateau_method(self, corrector: float = 0.0):
        n_of_fires = []
        for t in range(self.t_end):
            x = (self.alpha / self.q_max) ** 0.5 * t
            n_of_fires.append(ceil(x * (x + 1 + corrector)))

        return n_of_fires


# # some remains from previous version
# class TendToFire(TendToTSquared):
#     def __init__(self, files: dict, fire_curve: list, time_step: int = 5):
#         super().__init__(files)
#         self.lim_fire = np.array(fire_curve)
#         self.diameter = lcf2array(self.diameter)
#         self.rhr = lcf2array(self.rhr)
#         self.dt = time_step
#
#     def sum_n_check(self):
#         def check(t):
#             fc_t = np.interp(t, zip(*fc))
#             req_t = np.interp(t, zip(*self.lim_fire))
#             frac = fc_t / req_t
#             if abs(frac - 1) > 0.05:
#                 return False
#             else:
#                 return True
#
#         def act(t):
#             fc_t = np.interp(t, zip(*fc))
#             req_t = np.interp(t, zip(*self.lim_fire))
#             frac = fc_t / req_t
#             if frac < 1:
#                 pass
#                 # add
#             else:
#                 pass
#                 # remove
#
#         calc = True
#         fc = self.rhr.copy()
#         step = 0
#         dt = self.dt
#
#         while calc:
#             if check(step):
#                 step += dt
#             else:
#                 act(step - dt)
#                 check(step - dt / 2)
#
#         for t in range(self.t_end, self.dt):
#             pass
#


if __name__ == '__main__':
    def get_arguments(from_argv):
        parser = ar.ArgumentParser(description='Adjust times to ignition of multiple fires to achieve given fire curve')

        parser.add_argument('-l', '--localization', help='Path to DXF file with fire localization points',
                            required=True)
        parser.add_argument('-a', '--alpha', type=float, help='Summary fire growth factor (to tend to)', required=True)
        parser.add_argument('-f', '--fire', help='Path to single fire file', default='./locafi.txt')
        parser.add_argument('-c', '--config', help='Path to configuration file', default=None)
        parser.add_argument('-o', '--optimization', help='Optimization routine [iter/coeff]', default=None)
        parser.add_argument('-v', '--verbose', help='Extensive output', default=None)
        argums = parser.parse_args(args=from_argv)

        return argums


    args = get_arguments(argv[1:])


    def import_config(filepath):
        with open(filepath) as configfile:
            foo = [i.split() for i in configfile.readlines()]
        cfg = {}
        for i in range(len(foo)):
            cfg[foo[i][0]] = foo[i][1]

        print('[OK] config file imported')
        return cfg


    if args.config:  # if you use config file
        config = import_config(args.config)
        try:
            args.alpha = config['alpha']
        except KeyError:
            pass
        try:
            time_step = int(config['time_step'])
        except KeyError:
            time_step = 1

        a = TendToTSquared(args, time_step=time_step)

        try:
            if config['optimization'].lower() == 'coeff':
                if config['relative'].lower() in ['0', 'false', 'no', 'f', 'n']:
                    a.optimize_corr(float(config['precision']), relative=False)
                else:
                    a.optimize_corr(float(config['precision']))

            elif config['optimization'].lower() == 'iter':
                try:
                    bottom = float(config['bottom'])
                except KeyError:
                    bottom = -0.05
                try:
                    top = float(config['top'])
                except KeyError:
                    top = 0.1
                try:
                    initial_time = int(config['initial_time'])
                except KeyError:
                    initial_time = 10
                try:
                    optim_step = int(config['optim_step'])
                except KeyError:
                    optim_step = None   # global time_step will be taken

                a.optimize_iter(bottom=bottom, top=top, initial_time=initial_time, optim_step=optim_step)
            else:
                pass

        except KeyError:
            print('[WARNING] No optimization routine applied')

    else:  # settings from flags and defaults if not specified
        a = TendToTSquared(args)

        if args.optimization.lower() == 'iter':
            a.optimize_iter()
        elif args.optimization.lower() == 'coeff':
            a.optimize_corr()
        else:
            print('[WARNING] No optimization routine applied')

    a.make_lcfs()
    a.time_step = 10    # adjusting charts start time
    a.rhr_charts()
