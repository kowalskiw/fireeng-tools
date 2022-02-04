import matplotlib.pyplot as plt
import pandas as pd
from locale import *

'''This script makes chart of temperature from DEVC
specified in FDS. We use it to determine the temperature
at the exhaust fan entry. You should specify all the parameters
in the script.'''

# set filename with temperatures from FDS
plik = './klasa_temp.csv'

# horizontal value (maximum temperature for fan)
linia_pozioma = 400

# line size
l_size = 2

### chart bounds ###
ymin = 0
ymax = 500
xmin = 0
xmax = 1500

#font size parameters for plt labels
SMALL_SIZE = 8
MEDIUM_SIZE = 10
BIGGER_SIZE = 12
plt.rc('font', size=MEDIUM_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=BIGGER_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=BIGGER_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=BIGGER_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=MEDIUM_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title
axis_font = { 'size':BIGGER_SIZE} # fontzize of the legend

fig = plt.figure() 

# labels of axes (in Polish as a default)
x_lab = "Czas [s]"
y_lab = "Temperatura [°C]"

## plt.text(60,2.6,"Transient phase", size = 12)
df = pd.read_csv(plik, delimiter=',', decimal='.', skiprows = 1)

plt.plot(df["Time"], df["Temperature_MAX"], color='orange', linewidth=l_size, label="maksymalna")
plt.plot(df["Time"], df["Temperature_MASS MEAN"], color='royalblue', linewidth=l_size, label="średnia masowa")
plt.plot(df["Time"], df["Temperature_VOLUME MEAN"], color='gold', linewidth=l_size, label="średnia objętościowa")

plt.axhline(y=linia_pozioma, color='red', linewidth=l_size)

###plt.text(100,transm - 20,"T_oddym: %s s" %t_oddym, size = 12 )
###plt.text(100,transm -14,"Transmitancja: 95 % ", size = 12 )

plt.xlabel(x_lab, **axis_font)
plt.ylabel(y_lab, **axis_font)
ax = plt.gca()
ax.set_ylim([ymin,ymax])
ax.set_xlim([xmin,xmax])
plt.legend()
plt.grid(linestyle = ':', color = 'gray', linewidth = 0.8, alpha = 0.5)
plt.savefig('temperatura.png', format = 'png', dpi = 600)
plt.show()
