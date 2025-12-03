#from cinfdata import Cinfdata # https://github.com/CINF/cinf_database/blob/master/cinf_database/cinfdata.py
from PyExpLabSys.common.value_logger import LoggingCriteriumChecker as Checker
from PyExpLabSys.common.value_logger import ValueLogger
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time as timed
from datetime import datetime
import sys

# last working commit (before removing extra data for plot debugging)
# 98faa2410d7d9415fe52e2aabe1cf4a68eb39bc7

# Constants used for criterium checker
#TYPE = 'lin' # lin/log
TIMEOUT = 600 # seconds
#CRITERIUM = 0.1 # Ampere in this example
crits = {
    'pressure': {#
        'type': 'log',
        'criterium': 0.25,
        },
    'pressure_set': {#
        'type': 'log',
        'criterium': 0.5,
        },
    'speed': {#
        'type': 'lin',
        'criterium': 5,
        },
    'speed_set': {#
        'type': 'lin',
        'criterium': 1,
        },
    'speed_nom': {
        'type': 'lin',
        'criterium': 1,
        'timeout': 7200,
        },
    'temp_final_stage': {#
        'type': 'lin',
        'criterium': 1,
        },
    'temp_pump': {#
        'type': 'lin',
        'criterium': 1,
        },
    'temp_controller': {#
        'type': 'lin',
        'criterium': 1,
        },
    'power': {#
        'type': 'lin',
        'criterium': 20,
        },
    'current': {#
        'type': 'lin',
        'criterium': 0.1,
        },
    'voltage': {#
        'type': 'lin',
        'criterium': 1,
        'timeout': 1800
        },
    'operating_hours': {#
        'type': 'lin',
        'criterium': 0.5,
        #'timeout': 1859
        'timeout': 10859
        },
    'pressure_mode': {#
        'type': 'lin',
        'criterium': 0.5,
        'timeout': 1859
        },
    'standby_state': {#
        'type': 'lin',
        'criterium': 0.5,
        'timeout': 1859
        },
}
CODENAME = sys.argv[1]
if not CODENAME in crits.keys():
    raise ValueError(str(crits.keys()))
TYPE = crits.get(CODENAME)['type']
CRITERIUM = crits.get(CODENAME)['criterium']
try:
    TIMEOUT = crits.get(CODENAME)['timeout']
except KeyError:
    TIMEOUT = 600

# Plotting init
fig2, ax1 = plt.subplots()#plt.figure(2)
ax1.set_title('New model')
ax1.set_xlabel('Time (s)')
ax1.set_ylabel(CODENAME)
# Get reference data
load_time_zero = timed.time()
#Old header:
#;;;;;;;;;;;;
# New header:
#;;;;;;;;;;;;
#df1 = pd.read_csv('~/hiscroll46/HiScroll46_2025_1_29_21_31.csv', delimiter=';', header=0, index_col=False)
#df2 = pd.read_csv('~/hiscroll46/HiScroll46_2025_1_29_21_42.csv', delimiter=';', header=0, index_col=False)
#df3 = pd.read_csv('~/hiscroll46/HiScroll46_2025_1_29_21_49.csv', delimiter=';', header=0, index_col=False)
#df4 = pd.read_csv('~/hiscroll46/HiScroll46_2025_1_29_21_52.csv', delimiter=';', header=0, index_col=False)
#df5 = pd.read_csv('~/hiscroll46/HiScroll46_2025_1_29_21_58.csv', delimiter=';', header=0, index_col=False)
#df6 = pd.read_csv('~/hiscroll46/HiScroll46_2025_1_30_11_59.csv', delimiter=';', header=0, index_col=False)
#df7 = pd.read_csv('~/hiscroll46/HiScroll46_2025_1_31_17_53.csv', delimiter=';', header=0, index_col=False)
#df8 = pd.read_csv('~/hiscroll46/HiScroll46_2025_2_4_11_30.csv', delimiter=';', header=0, index_col=False)
#df9 = pd.read_csv('~/hiscroll46/HiScroll46_2025_2_10_14_15.csv', delimiter=';', header=0, index_col=False)
df10 = pd.read_csv('~/hiscroll46/HiScroll46_2025_3_14_13_52.csv', delimiter=';', header=0, index_col=False)
df11 = pd.read_csv('~/hiscroll46/HiScroll46_2025_4_1_14_52.csv', delimiter=';', header=0, index_col=False)
df12 = pd.read_csv('~/hiscroll46/HiScroll46_2025_4_1_14_54.csv', delimiter=';', header=0, index_col=False)

#df = pd.concat([df1, df2, df3, df4, df5, df6, df7, df8, df9])
#df = pd.concat([df5, df6, df7, df8, df9, df10, df11, df12])
df = pd.concat([df10, df11, df12])
#df = pd.concat([df11, df12])
df = df.rename(columns={
    'Timestamp': 'timestamp',
    'Pressure [hPa]': 'pressure',
    ' Pressure Set [hPa]': 'pressure_set',
    ' Speed [rpm]': 'speed',
    ' Speed Set [rpm]': 'speed_set',
    ' Speed Nom [rpm]': 'speed_nom',
    ' Temp Final Stage [C]': 'temp_final_stage',
    ' Temp Pump [C]': 'temp_pump',
    ' Temp Contr [C]': 'temp_controller',
    ' Power [W]': 'power',
    ' Current [A]': 'current',
    ' Voltage [V]': 'voltage',
    ' Operating Hours [h]': 'operating_hours',
    ' Standby': 'standby_state',
    ' Pressure Mode': 'pressure_mode',
})

# Timestamp format: 2025-01-29 21:31:40.531790
format_string = '%Y-%m-%d %H:%M:%S.%f'

time = np.zeros(len(df.timestamp))
for i, t in enumerate(df.timestamp):
    try:
        time[i] = datetime.timestamp(datetime.strptime(t, format_string))
    except ValueError:
        if len(t) == 19:
            t = t + ".0"
            time[i] = datetime.timestamp(datetime.strptime(t, format_string))
        else:
            print(i, repr(t))
            raise
t0 = time[0]
ydata = df.get(CODENAME)
#ydata[30:50] = 0

print('Data loaded in {} s'.format(timed.time() - load_time_zero))

# Get and plot old LoggingCriteriumChecker behaviour
class OldChecker(Checker):
    def event_handler(self, codename, type_, data_point, sign):
        """Skip pretrig sorting to simulate behaviour of LoggingCriteriumChecker"""
        return
    def timeout_handler(self, codename, now, value):
        return

checker = OldChecker(
    codenames=[CODENAME],
    types=[TYPE],
    criteria=[CRITERIUM],
    time_outs=[TIMEOUT],
    )
checker.deprecation_warning = False
old_time_start = timed.time()
for i, y in enumerate(ydata):
    checker.check(CODENAME, y, now=time[i])
old_time = timed.time() - old_time_start
old_data = np.array(checker.get_data(CODENAME))

# Plot reference data
ax1.plot(time - t0, ydata, 'bo-', label='Original data')
ax1.plot(old_data[:, 0] - t0, old_data[:, 1], 'r-', label='Original LCC')

print('Old checker run in {} s'.format(old_time))


# NEW DEFAULT
checker = Checker(
    codenames=[CODENAME],
    types=[TYPE],
    criteria=[CRITERIUM],
    time_outs=[TIMEOUT],
    grades=[0.1],
    )
checker.deprecation_warning = False
new_time_start = timed.time()
for i, y in enumerate(ydata):
    checker.check(CODENAME, y, now=time[i])
new_time = timed.time() - new_time_start
print('New checker run in {} s'.format(new_time))
new_data = np.array(checker.get_data(CODENAME))

# ValueLogger
class Reader(object):
    def __init__(self, time, data):
        self.counter = 0
        self.time = time
        self.data = data
        self.running = True

    def value(self):
        try:
            data = self.data[self.counter]
            self.time_value = self.time[self.counter]
            self.counter += 1
            return data
        except IndexError:
            self.running = False

reader_time_start = timed.time()
reader1 = Reader(time, np.asarray(ydata))
reader2 = Reader(time, np.asarray(ydata))
logger1 = ValueLogger(
    reader1,
    comp_type=TYPE,
    comp_val=CRITERIUM,
    maximumtime=TIMEOUT,
    model='sparse',
    grade=0.1,
    simulate=True,
    )
logger1.start()

while True:
    timed.sleep(1)
    if reader1.running is False:
        break
    print(reader1.running, reader2.running)

logger2 = ValueLogger(
    reader2,
    comp_type=TYPE,
    comp_val=CRITERIUM,
    maximumtime=TIMEOUT,
    model='event',
    grade=0.1,
    simulate=True,
    )
logger2.start()

while True:
    timed.sleep(1)
    if reader2.running is False:
        break
    print(reader1.running, reader2.running)

#for i, y in enumerate(ydata):
#    checker.check(CODENAME, y, now=time[i])
reader_time = timed.time() - reader_time_start
print('Double ValueLoggers run in {} s'.format(reader_time))
reader1_data = np.array(logger1.get_data())
reader2_data = np.array(logger2.get_data())

# Data stats
lref = len(ydata)
lold = len(old_data)
lnew = len(new_data)
lr1 = len(reader1_data)
lr2 = len(reader2_data)
#ltest = len(checker.extra['value'])
print('Number of points in raw data set: {} / 100%'.format(lref))
print('Number of points saved by old LCC: {} / {:1.1f}%'.format(lold, lold/lref*100))
print('Number of points saved by new LCC: {} / {:1.1f}%'.format(lnew, lnew/lref*100))
#print('Number of points saved by check_buffer_deviation: {}'.format(ltest))
print('Old LCC time lapse per point: {} s'.format(old_time/lref))
print('New LCC time lapse per point: {} s'.format(new_time/lref))
print('Number of points saved by old sparse ValueLogger: {} / {:1.1f}%'.format(lr1, lr1/lref*100))
print('Number of points saved by new event ValueLogger: {} / {:1.1f}%'.format(lr2, lr2/lref*100))

# Plot reference data
ax1.plot(new_data[:, 0] - t0, new_data[:, 1], 'go-', label='New LCC')
#t1 = checker.r_time
#p1 = checker.r_value

#ax2 = ax1.twinx()
#ax2.plot(t1-t0, p1, 'ko:', markersize=1)

#ax1.plot(checker.extra['time'] - t0, checker.extra['value'], 'yo', markersize=2)
#counter = 1
#mean_add = 0
#for times, mean in checker.means:
#    ax2.plot(np.array(times) - t0, [mean]*2, 'm:')
#    ax2.plot(np.array(times) - t0, [mean*50]*2, 'm-')
#ax1.set_yscale("log")
ax1.legend()

fig3, ax2 = plt.subplots()
ax2.set_title('ValueLogger')
ax2.set_xlabel('Time (s)')
ax2.set_ylabel(CODENAME)
# Plot reference data
ax2.plot(time - t0, ydata, 'bo-', label='Original data')
ax2.plot(reader1_data[:, 0] - t0, reader1_data[:, 1], 'ro-', label='Sparse VL')
ax2.plot(reader2_data[:, 0] - t0, reader2_data[:, 1], 'go-', label='Event VL')
ax2.legend()

plt.show()
