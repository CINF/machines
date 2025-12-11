import time
import requests
import datetime
from PyExpLabSys.common.value_logger import LoggingCriteriumChecker
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket, LiveSocket

import credentials

prefix = 'b313gas_'

#names = 'ar,n2,3_H2_Ar_left,3_H2_Ar_line,3_H2_Ar_right,Air_left,Air_line,Air_right,Ar_left,Ar_right,Ar_yard,CO2_left,CO2_line,CO2_right,CO_left,CO_line,CO_right,H2_left,H2_line,H2_right,He_left,He_line,He_right,N2_line,N2_yard,O2_left,O2_line,O2_right'.split(',')
names = [
    #'n2_evap_flow', ###
    'ar',
    'n2',
]
"""
    '3_H2_Ar_left',
    '3_H2_Ar_line',
    '3_H2_Ar_right',
    'Air_left',
    'Air_line',
    'Air_right',
    'Ar_left',
    'Ar_right',
    'CO2_left',
    'CO2_line',
    'CO2_right',
    'CO_left',
    'CO_line',
    'CO_right',
    'H2_left',
    'H2_line',
    'H2_right',
    'He_left',
    'He_line',
    'He_right',
    'N2_line',
    'O2_left',
    'O2_line',
    'O2_right',
]
"""
print(names) ###

def parse_dataline(line): # developed for version 7.3.0
    elements = line.split(' ')
    data = {}
    counter = 0
    for element in elements:
        if counter == 4:
            data[key] = (tstamp, value)
            counter = 0
        if counter == 0:
            key = element
            if key == 'VERSION':
                return data
        elif counter == 2:
            tstamp = int(element)
        elif counter == 3:
            value = float(element)
        counter += 1

"""
Der vil være et directory for hvert år (startende med 3test25 for i år) og for hver dag vil være en fil 'raadata.yyyy.mm.dd' som har loggede data.
Sidste linie I den fil vil være sidste logning (og det er PT sat op til at logge hvert 2. Minut)
De 2 datapunkter der er interessante mht logning af N2 og Ar forbrug fra tankanlæg er de kolonner der heder 'ar' og 'n2'.
Formatet for filen er for hvert 'tag':
Navn utime timestamp værdi
Og for gasflows er værdier altid i L/time.
"""

datasaver = ContinuousDataSaver(
    credentials.table,
    credentials.user,
    credentials.passwd,
    measurement_codenames=[prefix + name for name in names]
)

criteria = [1]*len(names)
for i, name in enumerate(names):
    if name == 'ar':
        criteria[i] = 10
    elif name == 'n2':
        criteria[i] = 100

logger = LoggingCriteriumChecker(
    codenames=[prefix + name for name in names],
    types=['lin']*len(names),
    criteria=criteria,
    time_outs=[3600]*len(names),
)

last_values = {}
for name in names:
    codename = prefix + name
    last_values[name] = {}
    point = datasaver.get_last_point(codename)
    last_values[name]['point'] = point
    if point:
        last_values[name]['date'] = datetime.datetime.fromtimestamp(point[0])
        logger.last_time[codename] = point[0]
        logger.last_values[codename] = point[1]

nones = [name for name in names if last_values[name]['point'] is None]

if len(nones) > 0:
    start_date = datetime.datetime(2025, 11, 14)
else:
    start_date = min([last_values[name].get('date') for name in names])

#response = requests.get('https://gasmon-b313.energy.dtu.dk/rig3/3test25/raadata.2025:11:14')
t, y = {}, {} ###
rt, ry = {}, {} ###
for name in names:
    t[name] = []
    y[name] = []
    rt[name] = []
    ry[name] = []
now = datetime.datetime(2025, 11, 19)
#now = datetime.datetime(2025, 11, 29)
#now = datetime.datetime.now()
while start_date <= now:
    suffix = str(start_date.year)[2:]
    year = start_date.year
    month = start_date.month
    day = start_date.day
    raw_file = f'https://gasmon-b313.energy.dtu.dk/rig3/3test{suffix}/raadata.{year}:{month:02d}:{day:02d}'
    print(raw_file)
    response = requests.get(raw_file)
    if response.status_code == 200:
        raw_file = response.text.split('\n')
        for line in raw_file:
            if line:
                data = parse_dataline(line)
            for name in names:
                new_point = data.get(name)
                if new_point is None:
                    continue
                if last_values[name]['point'] is None or new_point[0] > last_values[name]['point'][0]:
                    codename = prefix + name
                    if logger.check(codename, new_point[1], now=new_point[0]):
                        # Save data
                        
                        ### plot data
                        for point in logger.get_data(codename):
                            t[name].append(point[0])
                            y[name].append(point[1])
                    rt[name].append(new_point[0])
                    ry[name].append(new_point[1])

    # Next day
    start_date += datetime.timedelta(days=1)

import matplotlib.pyplot as plt
for i, name in enumerate(names):
    plt.figure(i+1)
    plt.plot(rt[name], ry[name], 'b-')
    plt.plot(t[name], y[name], 'ro-')
    plt.title(name)

plt.show()



