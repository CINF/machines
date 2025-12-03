#from cinfdata import Cinfdata # https://github.com/CINF/cinf_database/blob/master/cinf_database/cinfdata.py
from PyExpLabSys.common.value_logger import EjlaborateLoggingCriteriumChecker as Checker
from PyExpLabSys.common.database_saver import ContinuousDataSaver
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime
import sys
import time
import credentials

# Constants used for criterium checker
#TYPE = 'lin' # lin/log
TIMEOUT = 600 # seconds
#CRITERIUM = 0.1 # Ampere in this example
crits = {
    'pressure': {#
        'type': 'log',
        'criterium': 0.3,
#        'low_compare': 
        },
    'pressure_set': {#
        'type': 'log',
        'criterium': 0.3,
        },
    'speed': {#
        'type': 'lin',
        'criterium': 30,
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
    'run_hours': {#
        'type': 'lin',
        'criterium': 0.5,
        'timeout': 1859
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

KEYS = list(crits.keys())
#CODENAME_TRANSLATION = {key: 'test_hiscroll46_{}'.format(key) for key in keys}
    
# Start database saver
database_saver = ContinuousDataSaver(
    'dateplots_test_hiscroll46', credentials.user,
    credentials.passwd, ['test_hiscroll46_{}'.format(key) for key in KEYS],
    )
database_saver.start()

# Get reference data
#Old header:
#;;;;;;;;;;;;
# New header:
#;;;;;;;;;;;;
#df1 = pd.read_csv('~/hiscroll46/HiScroll46_2025_1_29_21_31.csv', delimiter=';', header=0, index_col=False)
#df2 = pd.read_csv('~/hiscroll46/HiScroll46_2025_1_29_21_42.csv', delimiter=';', header=0, index_col=False)
#df3 = pd.read_csv('~/hiscroll46/HiScroll46_2025_1_29_21_49.csv', delimiter=';', header=0, index_col=False)
#df4 = pd.read_csv('~/hiscroll46/HiScroll46_2025_1_29_21_52.csv', delimiter=';', header=0, index_col=False)
df5 = pd.read_csv('~/hiscroll46/HiScroll46_2025_1_29_21_58.csv', delimiter=';', header=0, index_col=False)
df6 = pd.read_csv('~/hiscroll46/HiScroll46_2025_1_30_11_59.csv', delimiter=';', header=0, index_col=False)
df7 = pd.read_csv('~/hiscroll46/HiScroll46_2025_1_31_17_53.csv', delimiter=';', header=0, index_col=False)
df8 = pd.read_csv('~/hiscroll46/HiScroll46_2025_2_4_11_30.csv', delimiter=';', header=0, index_col=False)
df9 = pd.read_csv('~/hiscroll46/HiScroll46_2025_2_10_14_15.csv', delimiter=';', header=0, index_col=False)
df10 = pd.read_csv('~/hiscroll46/HiScroll46_2025_3_14_13_52.csv', delimiter=';', header=0, index_col=False)
df11 = pd.read_csv('~/hiscroll46/HiScroll46_2025_4_1_14_52.csv', delimiter=';', header=0, index_col=False)
df12 = pd.read_csv('~/hiscroll46/HiScroll46_2025_4_1_14_54.csv', delimiter=';', header=0, index_col=False)

df13 = pd.read_csv('~/hiscroll46/HiScroll46_2025_4_1_14_59.csv', delimiter=';', header=0, index_col=False)
df14 = pd.read_csv('~/hiscroll46/HiScroll46_2025_4_3_15_16.csv', delimiter=';', header=0, index_col=False)
df15 = pd.read_csv('~/hiscroll46/HiScroll46_2025_4_7_8_45.csv', delimiter=';', header=0, index_col=False)
#df16 = pd.read_csv('~/hiscroll46/HiScroll46_2025_4_7_16_30.csv', delimiter=';', header=0, index_col=False)

#df = pd.concat([df5, df6, df7, df8, df9, df10, df11, df12], ignore_index=True)
df = pd.concat([df13, df14, df15], ignore_index=True)
#df = pd.concat([df5, df6], ignore_index=True)
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
    ' Operating Hours [h]': 'run_hours',
    ' Standby': 'standby_state',
    ' Pressure Mode': 'pressure_mode',
})

# Timestamp format: 2025-01-29 21:31:40.531790
format_string = '%Y-%m-%d %H:%M:%S.%f'

times = np.zeros(len(df.timestamp))
for i, t in enumerate(df.timestamp):
    try:
        times[i] = datetime.timestamp(datetime.strptime(t, format_string))
    except ValueError:
        if len(t) == 19:
            t = t + ".0"
            times[i] = datetime.timestamp(datetime.strptime(t, format_string))
        else:
            print(i, repr(t))
            raise
t0 = times[0]

1/0
for CODENAME in KEYS:
    #if CODENAME in ['pressure_mode', 'standby_state']:
    #    continue
    codename = f'test_hiscroll46_{CODENAME}'
    print(CODENAME, codename)
    
    if not CODENAME in crits.keys():
        raise ValueError(str(crits.keys()))
    TYPE = crits.get(CODENAME)['type']
    CRITERIUM = crits.get(CODENAME)['criterium']
    try:
        TIMEOUT = crits.get(CODENAME)['timeout']
    except KeyError:
        TIMEOUT = 600
    
    ydata = df.get(CODENAME)
    # NEW DEFAULT LOGGINGCRITERIUMCHECKER
    checker = Checker(
        codenames=[CODENAME],
        types=[TYPE],
        criteria=[CRITERIUM],
        time_outs=[TIMEOUT],
        grades=[0.1],
        )
    for i, y in enumerate(ydata):
        checker.check(CODENAME, y, time_=times[i])
    new_data = np.array(checker.get_data(CODENAME))

    # Data stats
    lref = len(ydata)
    lnew = len(new_data)
    print('Number of points in raw data set: {} / 100%'.format(lref))
    print('Number of points saved by new LCC: {} / {:1.1f}%'.format(lnew, lnew/lref*100))

    t0 = 0
    quit = False
    #while not quit:
    if True:
        #raw = input('Save "{}" data from {} to {} or plot?'.format(CODENAME, df.timestamp[0], df.timestamp[df.timestamp.size-1]))
        raw = 'save'
        if raw == 'save':
            print('Saving "{}" to database'.format(CODENAME))
            #for point in new_data:
            #    database_saver.save_point(f'test_hiscroll46_{CODENAME}', point)
            x_values = [float(i) for i in new_data[:, 0]]
            y_values = [float(i) for i in new_data[:, 1]]
            database_saver.save_points_batch(codename, x_values, y_values)
        elif raw == 'plot':
            # Plot reference data
            plt.figure(2)
            plt.title('New model')
            plt.plot(times - t0, ydata, 'bo-', label='Original data')
            plt.plot(new_data[:, 0] - t0, new_data[:, 1], 'k-', label='New LCC')
            plt.xlabel('Time (s)')
            plt.ylabel(CODENAME)

            plt.legend()
            plt.show()
        else:
            break
while database_saver.sql_saver.queue.qsize() > 0:
    print('{} %'.format((1 - database_saver.sql_saver.queue.qsize()/lnew)*100))
    n1 = database_saver.sql_saver.queue.qsize()
    time.sleep(5)
    n2 = database_saver.sql_saver.queue.qsize()
    rate = (n1-n2)/5
    if rate > 0:
        time_left = n2/rate
        if time_left > 60:
            print('{:.1f} minutes left'.format(time_left/60))
        else:
            print('{:.1f} seconds left'.format(time_left))
print('Data saved.')
