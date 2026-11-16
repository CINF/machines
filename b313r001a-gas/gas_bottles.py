import time
from pr_4511 import PR4511_4131
from PyExpLabSys.common.value_logger import LoggingCriteriumChecker
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket, LiveSocket

import credentials

PREFIX = 'b313gas_'
DEVICE_INFO = {
    3: {'name': '3_H2_Ar_left'},
    4: {'name': '3_H2_Ar_right'},
    5: {'name': 'Ar_left'},
    6: {'name': 'Ar_right'},
    7: {'name': 'CO2_left'},
    8: {'name': 'CO2_right'},
    9: {'name': 'He_left'},
    10: {'name': 'He_right'},
    11: {'name': 'N2_left'},
    12: {'name': 'N2_right'},
    13: {'name': 'O2_left'},
    14: {'name': 'O2_right'},
    17: {'name': 'Air_left'},
    18: {'name': 'Air_right'},
    19: {'name': '3_H2_Ar_line'},
    20: {'name': 'Ar_line'},
    21: {'name': 'CO2_line'},
    22: {'name': 'He_line'},
    23: {'name': 'N2_line'},
    24: {'name': 'O2_line'},
    25: {'name': 'Air_line'},
    130: {'name': 'CO_left'},
    230: {'name': 'CO_right'},
    131: {'name': 'H2_left'},
    231: {'name': 'H2_right'},
    132: {'name': 'CO_line'},
    232: {'name': 'H2_line'},
}

# Init devices
PORT = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FT2GCDHZ-if00-port0'
devices = {key: PR4511_4131(port=PORT, device_address=key) for key in DEVICE_INFO}
codenames = [PREFIX + DEVICE_INFO[i]['name'] for i in DEVICE_INFO]

datasaver = ContinuousDataSaver(
    credentials.table,
    credentials.user,
    credentials.passwd,
    measurement_codenames=codenames,
)
datasaver.start()

livesocket = LiveSocket('313 gas bottle pressures', codenames=codenames)
livesocket.start()

logger = LoggingCriteriumChecker(
    codenames=codenames,
    types=['lin'] * len(DEVICE_INFO),
    criteria=[1] * len(DEVICE_INFO),
    time_outs=[3600] * len(DEVICE_INFO),
)

while True:
    for key in DEVICE_INFO:
        codename = PREFIX + DEVICE_INFO[key]['name']
        # Do own conversion from full scale to get more decimals
        pressure = devices[key].read_relative_value() * 250  # unit: bar
        print(codename, pressure)
        if logger.check(codename, pressure):
            print('Check!')
            for point in logger.get_data(codename):
                print(codename, point)
                datasaver.save_point(codename, point)

    time.sleep(1)
