#from cinfdata import Cinfdata # https://github.com/CINF/cinf_database/blob/master/cinf_database/cinfdata.py
#from PyExpLabSys.common.value_logger import EjlaborateLoggingCriteriumChecker as Checker
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
    'standby_state': {#
        'type': 'lin',
        'criterium': 0.5,
        'timeout': 1859
        },
}

AVG = True
if AVG:
    add_code = '_avg'
    add_file = '_avg'
else:
    add_code = '_raw'
    add_file = ''

keys = [
        'magfield_x',
        'magfield_y',
        'magfield_z',
        'magcomp_x',
        'magcomp_y',
        'magcomp_z',
        'systron_psu_voltage',
]

# Start database saver
database_saver = ContinuousDataSaver(
    'dateplots_vision_mymetalroom', credentials.vision_user,
    credentials.vision_passwd, ['vision_{}{}'.format(key, add_code) for key in keys],
    )
database_saver.start()

finished = [
    #'Vision_Mag_field_2023_9_26_17_13.csv',
    
]

filelist = [
    #'Vision_Mag_field_2023_9_27_10_8.csv',
    #'Vision_Mag_field_2023_9_28_12_17.csv',
    #'Vision_Mag_field_2023_9_28_15_14.csv',
    #'Vision_Mag_field_2023_9_28_15_15.csv',
    #'Vision_Mag_field_2023_9_29_6_31.csv',
    #'Vision_Mag_field_2023_9_29_6_33.csv',
    #'Vision_Mag_field_2023_9_29_14_34.csv',
    #'Vision_Mag_field_2023_10_2_10_6.csv',
    #'Vision_Mag_field_2023_10_3_13_17.csv',
    #'Vision_Mag_field_2023_10_3_13_52.csv',
    #'Vision_Mag_field_2023_10_4_15_24.csv',
    #'Vision_Mag_field_2023_10_4_15_42.csv',
    #'Vision_Mag_field_2023_10_5_13_48.csv',
    #'Vision_Mag_field_2023_10_5_13_51.csv',
    #'Vision_Mag_field_2023_10_6_16_24.csv',
    #'Vision_Mag_field_2023_10_6_16_27.csv',
    #'Vision_Mag_field_2023_10_9_11_29.csv',
    #'Vision_Mag_field_2023_10_9_11_35.csv',
    #'Vision_Mag_field_2023_10_10_11_40.csv',
    #'Vision_Mag_field_2023_10_16_10_34.csv',
    #'Vision_Mag_field_2023_10_18_15_17.csv',
    #'Vision_Mag_field_2023_10_18_15_32.csv',
    #'Vision_Mag_field_2023_10_18_15_48.csv', ### AVG
    #
    #'Vision_Mag_field_2023_10_18_15_57.csv',
    #'Vision_Mag_field_2023_10_19_9_11.csv',
    #'Vision_Mag_field_2023_10_19_9_17.csv',
    #'Vision_Mag_field_2023_10_24_18_41.csv',
    #'Vision_Mag_field_2023_11_1_13_45.csv',
    #'Vision_Mag_field_2023_11_2_17_17.csv',
    #'Vision_Mag_field_2023_11_3_10_17.csv',
    #'Vision_Mag_field_2023_11_3_11_28.csv',
    #'Vision_Mag_field_2023_11_13_14_51.csv',
    #'Vision_Mag_field_2023_11_27_15_17.csv',
    #'Vision_Mag_field_2023_12_11_11_31.csv',
    #'Vision_Mag_field_2023_12_12_10_19.csv',
    #'Vision_Mag_field_2023_12_12_15_19.csv',
    #'Vision_Mag_field_2023_12_12_15_44.csv',
    #'Vision_Mag_field_2023_12_12_15_56.csv',
    #'Vision_Mag_field_2023_12_12_16_10.csv',
    #'Vision_Mag_field_2023_12_12_16_20.csv',
    #'Vision_Mag_field_2023_12_12_16_39.csv',
    #
    #'Vision_Mag_field_2024_1_11_13_1.csv',
    #'Vision_Mag_field_2024_1_17_16_19.csv',
    #'Vision_Mag_field_2024_2_22_16_52.csv',
    #'Vision_Mag_field_2024_2_28_13_14.csv',
    #'Vision_Mag_field_2024_3_13_11_42.csv',
    #'Vision_Mag_field_2024_3_27_14_25.csv',
    #'Vision_Mag_field_2024_4_3_10_21.csv',
    #'Vision_Mag_field_2024_4_8_13_34.csv',
    #'Vision_Mag_field_2024_4_11_10_4.csv',
    #'Vision_Mag_field_2024_4_19_10_23.csv',
    #'Vision_Mag_field_2024_4_19_10_57.csv',
    #'Vision_Mag_field_2024_4_30_17_30.csv',
    #'Vision_Mag_field_2024_5_4_8_17.csv',
    #'Vision_Mag_field_2024_5_8_10_6.csv',
    #'Vision_Mag_field_2024_6_2_23_21.csv',
    #'Vision_Mag_field_2024_7_31_10_27.csv',
    #'Vision_Mag_field_2024_8_28_12_7.csv',
    #'Vision_Mag_field_2024_9_2_12_39.csv',
    #'Vision_Mag_field_2024_9_9_14_52.csv',
    #'Vision_Mag_field_2024_9_24_10_28.csv',
    #'Vision_Mag_field_2024_9_27_8_38.csv',
    #'Vision_Mag_field_2024_10_1_16_45.csv',
    #'Vision_Mag_field_2024_10_28_7_17.csv',
    #'Vision_Mag_field_2024_11_26_13_31.csv',
    #
    #'Vision_Mag_field_2025_1_15_5_17.csv',
    #'Vision_Mag_field_2025_1_28_18_33.csv',
    #'Vision_Mag_field_2025_1_29_9_26.csv',
    #'Vision_Mag_field_2025_1_29_12_7.csv',
    #'Vision_Mag_field_2025_2_14_16_14.csv',
    #'Vision_Mag_field_2025_3_11_11_33.csv',
    #'Vision_Mag_field_2025_3_11_21_20.csv',
    #'Vision_Mag_field_2025_5_21_17_43.csv',
    'Vision_Mag_field_2025_5_28_13_48.csv'
]


# Get reference data
#Old header:
#;;;;;;;;;;;;
# New header:
#;;;;;;;;;;;;
for i, filename in enumerate(filelist):
    #if i==1:
    #    1/0
    filename = filename.replace('.csv', add_file + '.csv')
    print('Reading: ', filename)
    df = pd.read_csv('~/vision_mag_field/' + filename, delimiter=';', header=0, index_col=False)
    df = df.rename(columns={
        'Timestamp': 'timestamp',
        'X-field': 'magfield_x',
        'Y-field': 'magfield_y',
        'Z-field': 'magfield_z',
        'X-current': 'magcomp_x',
        'Y-current': 'magcomp_y',
        'Z-current': 'magcomp_z',
        'PSU Voltage': 'systron_psu_voltage',
    })
    df = df[df['systron_psu_voltage'].notna()]

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

    for key in keys:
        codename = 'vision_' + key + add_code
        print(codename)
        
        ydata = df.get(key)
        # NEW DEFAULT LOGGINGCRITERIUMCHECKER
        #checker = Checker(
        #    codenames=[CODENAME],
        #    types=[TYPE],
        #    criteria=[CRITERIUM],
        #    time_outs=[TIMEOUT],
        #    grades=[0.1],
        #    )
        #for i, y in enumerate(ydata):
        #    checker.check(CODENAME, y, time_=times[i])
        #new_data = np.array(checker.get_data(CODENAME))
        new_data = np.array(list(zip(list(times), ydata)))
        new_data = new_data[np.isfinite(new_data[:, 1])]
        # Data stats
        lref = len(ydata)
        #lnew = len(new_data)
        print('Number of points in raw data set: {} / 100%'.format(lref))
        #print('Number of points saved by new LCC: {} / {:1.1f}%'.format(lnew, lnew/lref*100))

        t0 = 0
        quit = False
        #while not quit:
        if True:
            #raw = input('Save "{}" data from {} to {} or plot?'.format(CODENAME, df.timestamp[0], df.timestamp[df.timestamp.size-1]))
            raw = 'save'
            if raw == 'save':
                print('Saving "{}" to database'.format(codename))
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
                plt.ylabel(key)

                plt.legend()
                plt.show()
            else:
                break
    while database_saver.sql_saver.queue.qsize() > 0:
        print('{} left'.format(database_saver.sql_saver.queue.qsize()))
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
