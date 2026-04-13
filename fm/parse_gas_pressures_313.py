import time
import requests
import datetime
from PyExpLabSys.common.value_logger import LoggingCriteriumChecker
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket, LiveSocket

import credentials

prefix = 'b313gas_'

names = [
    '3_H2_Ar_left',
    '3_H2_Ar_line',
    '3_H2_Ar_right',
    #
    'Air_left',
    'Air_line',
    'Air_right',
    #
    'Ar_left',
    'Ar_right',
    #'Ar_line', ### IS MISSING ###
    #
    'CO2_left',
    'CO2_line',
    'CO2_right',
    #
    'CO_left',
    'CO_line',
    'CO_right',
    #
    'H2_left',
    'H2_line',
    'H2_right',
    #
    'He_left',
    'He_line',
    'He_right',
    #
    #'N2_left', ### IS MISSING ###
    'N2_line',
    #'N2_right', ### IS MISSING ###
    #
    'O2_left',
    'O2_line',
    #'O2_right', ### IS MISSING ### (-0.62 bar since beginning of January)
]
print(names)  ###


def parse_dataline(line):  # developed for version 7.3.0
    elements = line.split(' ')
    data = {}
    counter = 0
    for element in elements:
        if counter == 4:
            if value >= 0:
                data[key] = (tstamp, value)
            else:
                data[key] = None
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
    measurement_codenames=[prefix + name for name in names],
)
datasaver.start()

livesocket = LiveSocket('fm testrig', codenames=[*names, 'poke'])
livesocket.start()

criteria = [1] * len(names)
for i, name in enumerate(names):
    if name == 'ar':
        criteria[i] = 10
    elif name == 'n2':
        criteria[i] = 100

logger = LoggingCriteriumChecker(
    codenames=[prefix + name for name in names],
    types=['lin'] * len(names),
    criteria=criteria,
    time_outs=[3600] * len(names),
)

last_values = {}
for name in names:
    codename = prefix + name
    last_values[name] = {}
    print('Getting last point for {}'.format(codename))
    point = datasaver.get_last_point(codename)
    last_values[name]['point'] = point
    if point:
        last_values[name]['date'] = datetime.datetime.fromtimestamp(point[0])
        print('{} - {}'.format(last_values[name]['date'], point[1]))
        logger.last_time[codename] = point[0]
        logger.last_values[codename] = point[1]

nones = [name for name in names if last_values[name]['point'] is None]

if len(nones) > 0:
    start_date = datetime.datetime(2025, 11, 14)
else:
    start_date = min([last_values[name].get('date') for name in names])

# response = requests.get('https://gasmon-b313.energy.dtu.dk/rig3/3test25/raadata.2025:11:14')
t, y = {}, {}  ###
rt, ry = {}, {}  ###
for name in names:
    t[name] = []
    y[name] = []
    rt[name] = []
    ry[name] = []

change_day = False
timer = start_date
last_timer = start_date
handle_midnight = False
while True:
    if timer.day - last_timer.day > 0:
        # Midnight has passed
        handle_midnight = True
        timer = timer - datetime.timedelta(days=1)
    suffix = str(timer.year)[2:]
    year = timer.year
    month = timer.month
    day = timer.day

    raw_file = f'https://gasmon-b313.energy.dtu.dk/rig3/3test{suffix}/raadata.{year}:{month:02d}:{day:02d}'
    print(raw_file)
    response = requests.get(raw_file)
    if response.status_code == 200:
        raw_file = response.text.split('\n')
        for line in raw_file:
            if line:
                data = parse_dataline(line)
            else:
                break
            for name in names:
                new_point = data.get(name)
                if new_point is None:
                    continue
                if (
                    last_values[name]['point'] is None
                    or new_point[0] > last_values[name]['point'][0]
                ):
                    codename = prefix + name
                    if logger.check(codename, new_point[1], now=new_point[0]):
                        for point in logger.get_data(codename):
                            # Save data
                            try:
                                livesocket.set_point(name, point)
                            except:
                                print('livesocket error')
                            datasaver.save_point(codename, point)
                    last_values[name]['point'] = new_point

    # Next event
    if handle_midnight:
        timer = timer + datetime.timedelta(days=1)
        handle_midnight = False
    last_timer = timer
    timer = timer + datetime.timedelta(days=1)
    if timer >= datetime.datetime.now():
        print('{} - Waiting 10 minutes..'.format(datetime.datetime.now()))
        counter = 0
        # Activity marker
        marks = ['\\', '|', '/', '-']
        for i in range(600):
            print(marks[counter] + '  ', end='\r')
            time.sleep(1)
            # if i%10 == 9:
            #    livesocket.set_point_now('poke', i)
            counter += 1
            if counter > 3:
                counter = 0
        timer = datetime.datetime.now()
