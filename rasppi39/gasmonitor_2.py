"""This script monitors the Vortex gas alarm system in building 307
and logs the output

For the status logs:
 * Numbers 1-? are detectors
 * 255 is the system power status
 * 254 is the system status
"""

import time
#import json

#import credentials
#from PyExpLabSys.common.sockets import LiveSocket, DateDataPullSocket
#from PyExpLabSys.common.utilities import get_logger, activate_library_logging
# Set log filesize to 10 MB
#LOGGER = get_logger('b307gasalarm', level='debug')
#LOGGER = get_logger('b307gasalarm', level='info')
#import MySQLdb

if __name__ == '__main__':
    import credentials
    from central_config import CENTRAL
    from common.gasalarm.vortex_logger import GasAlarmMonitor, ResetException
    central_number = 2
    reset = True
    codenames = CENTRAL[central_number]['codenames']
    settings = CENTRAL[central_number]['settings']
    kwargs = {
        'port': settings['port'],
        'codename_channel_dict': codenames,
        'credentials': credentials,
        'slave_address': settings['slave'],
        'vortex_number': central_number,
        'floor': -1,
    }

    while True:
        try:
            if reset:
                gas_alarm_monitor = GasAlarmMonitor(**kwargs)
                time.sleep(1)
                reset = False
            gas_alarm_monitor.main()
        except KeyboardInterrupt:
            gas_alarm_monitor.close()
            break
        #except (IOError, MySQLdb.OperationalError) as exception:
        #    print("No com with instrument. Sleep 300s and try again.")
        #    print(exception)
        #    time.sleep(300)
        #    # Reset the monitor
        #    reset = True
        #    continue
        except Exception as exception:
            print(exception)
            gas_alarm_monitor.close()
            raise exception

    time.sleep(2)
    print('Program has stopped')
