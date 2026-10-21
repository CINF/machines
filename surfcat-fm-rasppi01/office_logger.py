""" Pressure and temperature logger """
from __future__ import print_function
import threading
import time
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.honeywell_6000 as honeywell_6000
import PyExpLabSys.common.utilities
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
PyExpLabSys.common.utilities.ERROR_EMAIL = 'jejsor@fysik.dtu.dk'

LOGGER = get_logger('FM office temperature logger', level='WARN', file_log=True,
                    file_name='temp_control.log', terminal_log=False, email_on_warnings=False)

LOGGER.warning('Program started')


class Reader(threading.Thread):
    """ Pressure reader """
    def __init__(self, honeywell):
        threading.Thread.__init__(self)
        self.honeywell = honeywell
        self.temperature = None
        self.humidity = None
        self.quit = False
        self.ttl = 20

    def value(self, channel):
        """ Read temperature and  pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel == 1:
                return_val = self.temperature
            if channel == 2:
                return_val = self.humidity
        return return_val

    def run(self):
        while not self.quit:
            time.sleep(0.2)
            try:
                self.humidity, self.temperature = self.honeywell.read_values()
            except OSError:
                print('OSError I2C')
                self.ttl -= 1
                if self.ttl < 0:
                    print('Too many errors - quitting!')
                    self.quit = True
                continue
            print(self.humidity, self.temperature)
            self.ttl = 50


def main():
    """ Main function """
    hih_instance = honeywell_6000.HIH6130()
    reader = Reader(hih_instance)
    reader.daemon = True
    reader.start()

    time.sleep(5)

    codenames = ['office_313_231_temperature', 'office_313_231_humidity']

    loggers = {}
    loggers[codenames[0]] = ValueLogger(reader, comp_val=1, comp_type='lin', channel=1)
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(reader, comp_val=1, comp_type='lin', channel=2)
    loggers[codenames[1]].start()

    livesocket = LiveSocket('FM Office 312 Air Logger', codenames)
    livesocket.start()

    socket = DateDataPullSocket('FM Office 312 Air Logger', codenames,
                                timeouts=[1.0] * len(loggers))
    socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_offices_312',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    error = 0
    while reader.is_alive():
        print(True)
        time.sleep(0.5)
        for name in codenames:
            value = loggers[name].read_value()
            try:
                livesocket.set_point_now(name, value)
                error = 0
            except OSError as msg:
                error += 0.5
                LOGGER.warning('Error count: {} ({})'.format(error, msg))
            socket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(value)
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    while True:
        try:
            main()
        except OSError as exception:
            print('!!!')
            LOGGER.warning("Got '{}', restarting in 300s".format(exception))
            time.sleep(300)
            #raise
        except KeyboardInterrupt:
            break
