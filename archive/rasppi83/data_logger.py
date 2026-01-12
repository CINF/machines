""" Data logger for the mobile gas wall """
from __future__ import print_function
import threading
import logging
import time
import minimalmodbus
import serial
from PyExpLabSys.common.socket_clients import DateDataPullClient
from PyExpLabSys.common.value_logger import ValueLogger, LoggingCriteriumChecker
from PyExpLabSys.common.database_saver import ContinuousDataSaver, DataSetSaver, CustomColumn
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
import numpy as np
import os
import sys
python2_and_3(__file__)

from PyExpLabSys.common.utilities import get_logger

FORMAT = '%(asctime)s -- %(name)s:%(message)s'
logging.basicConfig(filename="temperature.log", format=FORMAT, level=logging.WARNING)
LOGGER = logging.getLogger('data_logger')
#logging.basicConfig(filename="temperature.log", format=FORMAT, level=logging.WARNING)
#LOGGER = get_logger('data_logger', file_name="temperature.log", level=logging.WARNING, file_max_byte#s=104857, file_backup_count=5)

class TcReader(threading.Thread):
    """ Communicates with the Omega ?? """
    
    def __init__(self, port, datasocket, RTU, register_nbr, codename, crit_logger=None, db_logger=None, output=False, logger=LOGGER):
        super().__init__()
        self.register_nbr = register_nbr    
        self.logger = logger
        ###self.logger.info('Initializing connection')
        self.comm = minimalmodbus.Instrument(port, 1)
        self.comm.serial.parity = serial.PARITY_EVEN
        self.comm.serial.bytesize = 8
        self.comm.serial.stopbits = 1
        self.comm.serial.baudrate = 9600
        self.comm.serial.mode = minimalmodbus.MODE_RTU
        #self.comm.precalculate_read_size = False
        #self.comm.debug = True
        #self.comm.serial.timeout = 1
        self.RTU = RTU
        if RTU == True:
            self.comm.serial.timeout = 0.1
        elif RTU == False:
            self.comm.serial.timeout = 0.5
        error = 0
        while error < 10:
            try:
                self.temperature = self.comm.read_register(self.register_nbr[0], 1, signed=True)
                break
            except OSError:
                error = error
                '''
                if error > 9:
                self.temperature = None
                exit('Error in communication with TC reader')
                self.logger.info('Connection to Omega established')
                #if self.temperature < -1000:
                #    self.temperature = None
                #threading.Thread.__init__(self)
                '''
        self.quit = False
        self.datasocket = datasocket
        self.crlogger = crit_logger
        self.db_logger = db_logger
        self.codename = codename
        ###self.logger.info('TcReader ready')
        self.output = output

   # def value(self):
        """ Return current value of reader """
    #    if (self.temperature < 1050) and (self.temperature > -300):
     #       return self.temperature
   
    def stop(self):
        """ Close thread properly """
        self.quit = True
        #self.datasocket.stop()
        if self.db_logger is not None:
            self.db_logger.stop()
        
    def run(self):
        time.sleep(0.5)
        error = 0
        lasttime = time.time()
        t0 = time.time()
        self.temperatures = np.zeros(len(self.register_nbr))
        try:
            ###self.logger.info('Entering while loop')
            while self.isAlive() and not self.quit:
                # Delay loop communication
                time.sleep(0.05)
                for i in range(len(self.register_nbr)):
                    try:
                        self.temperature = self.comm.read_register(self.register_nbr[i], 1, signed=True)
                        self.temperatures[i] = self.temperature
                        if self.temperature < -250:
                            self.temperature = None
                        if error > 0:
                            error = 0
                        # Save points to sockets
                        self.datasocket.set_point_now(self.codename[i], self.temperature)
                        if self.crlogger is not None and self.db_logger is not None and self.temperature is not None:
                                    if self.crlogger.check(self.codename[i], self.temperature):
                                        self.db_logger.save_point_now(self.codename[i], self.temperature)
                                        ###self.logger.debug(self.codename[i] + ': ' + str(self.temperature))
                        if self.output:
                            print(self.temperature, time.time()-t0, time.time()-lasttime)
                            lasttime = time.time()
                    except Exception as e:
                        error += 1
                        ###self.logger.warning('Error value: {}'.format(error), exc_info=True)
                        #if error > 9:
                        #    self.stop()
                        #    raise
        except KeyboardInterrupt:
            ###self.logger.debug('Force quit activated (CTRL+C)')
            self.stop()
        ###self.logger.debug('Logger stopped by exiting run function properly')

CODENAMES = {'Sample': 'omicron_tpd_sample_temperature',
             'Base': 'omicron_tpd_temperature',
             'Setpoint': 'omicron_tpd_setpoint'
             }
'''
CODENAMES = {'Base': 'omicron_tpd_temperature',
             'Setpoint': 'omicron_tpd_setpoint'
}
'''
    
def main():
    """ Main function """
    t0 = time.time()
    ports = dict()
    ports['Sample'] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTY5BU0H-if00-port0'
   #ports['Setpoint'] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWEAFPS-if00-port0'
    ports['Base'] =   '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTY3GX3T-if00-port0'

    # Set up criterium logger
    logger = LoggingCriteriumChecker(
        codenames=list(CODENAMES.values()),
        types=['lin', 'lin', 'lin'],
        criteria=[0.73, 0.73, 0.73],
        time_outs=[100, 500, 100],
        low_compare_values=[-200, -200, -200],
        )

    # Set up pullsocket
    datasocket = DateDataPullSocket('mgw_temp', list(CODENAMES.values()), timeouts=4, port=9000)
    datasocket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_omicron',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    #measurement_codenames=list(CODENAMES.values()),
                                    measurement_codenames=[CODENAMES['Base']],
    )
    db_logger.start()

    logger1 = LOGGER.getChild('Base_reader')
    base_logger = TcReader(ports['Base'], datasocket, False, [4096], [CODENAMES['Base']], crit_logger=logger, db_logger=db_logger, logger=logger1)
    base_logger.start()

    logger2 = LOGGER.getChild('Sample_reader')
    #4096,4097
    #2,3
    sample_logger = TcReader(ports['Sample'], datasocket, True, [4096, 4097], [CODENAMES['Sample'], CODENAMES['Setpoint']], logger=logger2)
    sample_logger.start()
    
   # logger3 = LOGGER.getChild('Setpoint_reader')
   # setpoint_logger = TcReader(ports['Setpoint'], datasocket, True, 3, codename=CODENAMES['Setpoint'], logger=logger3)
   # setpoint_logger.start()

    # Option for direct db logging. Passed as "logging", "logging = True", or "True" 
    try:
        argument = str(sys.argv[1]).lower()
        if argument == 'logging' or argument == 'logging=true' or argument  == 'true':
            db_logging_bool = True
        else:
            db_logging_bool = False
    except:
        db_logging_bool = False

    if db_logging_bool == True:
        db_direct_logger = DataSetSaver(
            'measurements_omicron',
            'xy_values_omicron',
            credentials.user,
            credentials.passwd,
        )
        db_direct_logger.start()

        time.sleep(2)

        #Pass comment (name of measurement on surfcatdata)  as second argument. If nothing is passed, it is named "TPD chamber temperatures". 
        try:
            logging_name = sys.argv[2]
        except:
            logging_name = 'TPD chamber temperatures'
        meta_data = {
            "Time": CustomColumn(t0, "FROM_UNIXTIME(%s)"),
            "comment": logging_name,
            "type": 5,
            "sem_voltage": -1,
            "preamp_range": -1,
        }
        for name in list(CODENAMES):
            meta_data["mass_label"] = str(name) + ' temperature'
            db_direct_logger.add_measurement(str(name)+ ' temperature', meta_data) #is this correct?
        meta_data["mass_label"] = 'Sample temperature (DATAQ)'
        db_direct_logger.add_measurement('Sample temperature (DATAQ)', meta_data)
            
    # Print values
    old_temp = -1
    last_save = 0
    running_status = ''
    t_dead = 0
    clear_time = 0
    time.sleep(0.5)
    os.system('clear')
    string = '{:6s}' + ' '*2 + '{: <8.4}' + ' '*2 + '{: <8.4}' + ' '*4 + '{: <8.4}' + ' '*12 + '{: <8.4}'
    header = ('Error ' + '  ' + 'Base [C]' + '  ' + 'Sample [C]' + '  ' + 'Sample (DATAQ) [C]' + '  ' + 'Setpoint [C]')
    print(header)
    while True:
        running_status = 'None'
        if t_dead >= 100:
            sample_logger.stop()
            sample = None
            setpoint = None
            logger2 = LOGGER.getChild('Sample_reader')
            #4096,4097
            #2,3
            try:
                sample_logger = TcReader(ports['Sample'], datasocket, True, [4096,4097], [CODENAMES['Sample'],CODENAMES['Setpoint']], logger=logger2)
                sample_logger.start()
            except:
                continue
            t_dead = 0
        if clear_time >= 100:
            os.system('clear')
            print('\r' + header)
            clear_time = 0
        try:
            time.sleep(1/60)
            try:
                dataq_data = DateDataPullClient('10.54.7.193', 'omicron_TPD_sample_temp', exception_on_old_data=True, port=9002, timeout = 0.1)
                dataq_data = dataq_data.get_field('omicron_T_sample')
                dataq_temp = dataq_data[1]
                if dataq_temp <= -199.8:
                    dataq_temp = '---'
            except:
                dataq_temp = '---'
                running_status += 'DATAQ'
            try:
                sample = sample_logger.temperatures[0]
                setpoint = sample_logger.temperatures[1]
            except:
                sample = None
                setpoint = None
            if sample is None or sample <=-200:
                sample = '---'
                t_dead += 1
                running_status +='Sample'
            base = base_logger.temperature
            if base is None:
                base = '---'
            if setpoint is None:
                setpoint = '---'
            if len(running_status) > 6:
                running_status = '>1 ERR'
            print('\r', end ='', flush = False)
            if type(dataq_temp) == str or type(sample) == str or type(base) == str or type(setpoint) == str:
                print(string.format(running_status, base, sample, dataq_temp, setpoint), end='', flush=False)
            else:
                print(string.format(running_status, round(base,1), round(sample,1), round(dataq_temp,1), round(setpoint,1)), end='', flush=False)
            clear_time += 1
        #except ValueError:
         #  running_status = 'Sample'
           #print('ValueError')
           #print(repr(measurement.temperature), type(measurement.temperature))
           #print(repr(sample_logger.temperature))
        except KeyboardInterrupt:
            base_logger.stop()
            sample_logger.stop()
            time.sleep(2)
            LOGGER.info('\nTcReaders stopped')
            datasocket.stop()
            db_direct_logger.stop()
            LOGGER.info('Pullsocket stopped\nExiting.')
            break

        # Logging directly to database
        if db_logging_bool == 'True':
            t_now = time.time() - t0
            logger_temps = {}
            logger_temps['Sample'] = sample_logger.temperatures[0]
            logger_temps['Setpoint'] = sample_logger.temperatures[1]
            logger_temps['Base'] = base_logger.temperature

            for name in list(CODENAMES):
                value = logger_temps[name]
                if value != old_temp or t_now - last_save > 5 :
                    db_direct_logger.save_point(str(name) + ' temperature' , (t_now*1000, value))
                    old_temp = value
                    last_save = t_now
            try:
                db_direct_logger.save_point('Sample temperature (DATAQ)', (dataq_data[0]-t0, dataq_data[1]))
            except:
                continue

if __name__ == '__main__':
    main()
