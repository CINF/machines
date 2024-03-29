"""This script monitors the Vortex gas alarm system in building 307
and logs the output

For the status logs:
 * Numbers 1-? are detectors
 * 255 is the system power status
 * 254 is the system status
"""

import time
import json

from PyExpLabSys.drivers.crowcon3 import Vortex
from PyExpLabSys.common.sockets import LiveSocket, DateDataPullSocket
from PyExpLabSys.common.utilities import get_logger, activate_library_logging
from PyExpLabSys.common.database_saver import ContinuousDataSaver
# Set log filesize to 10 MB
LOGGER = get_logger('b307gasalarm', level='debug')
#LOGGER = get_logger('b307gasalarm', level='info')
import MySQLdb

activate_library_logging('PyExpLabSys.drivers.crowcon3', logger_to_inherit_from=LOGGER,
                         level='warn')
#activate_library_logging('PyExpLabSys.drivers.crowcon3', logger_to_inherit_from=LOGGER,
#                         level='info')

class ResetException(Exception):
    pass

class GasAlarmMonitor(object):
    """Class that monitors the gas alarm the building 307"""

    def __init__(self, port, codename_channel_dict, credentials, slave_address=1, vortex_number=1,
                 floor=None, db_logger=None):
        # Start logger
        self.user = credentials.USERNAME
        self.floor = floor
        self.codenames = codename_channel_dict
        self.vortex_number = vortex_number
        #codenames = ['B307_gasalarm_CO_139_1', 'B307_gasalarm_H2_139_1',
        #             'B307_gasalarm_CO2_139_1', 'B307_gasalarm_CO_139_2',
        #             'B307_gasalarm_CO2_139_2', 'B307_gasalarm_H2_139_2',
        #             'B307_gasalarm_CO2_147', 'B307_gasalarm_H2_147',
        #             'B307_gasalarm_CO_147', 'B307_gasalarm_CO_149',
        #             'B307_gasalarm_CO2_149', 'B307_gasalarm_H2_149']
        ###self.db_logger = ContinuousLogger(table=credentials.TABLE,#'dateplots_b307gasalarm',
        ###                                  username=credentials.USERNAME,
        ###                                  password=credentials.PASSWORD,
        ###                                  measurement_codenames=list(self.codenames.values()))
        self.db_logger = ContinuousDataSaver(
            continuous_data_table=credentials.TABLE,
            username=credentials.USERNAME,
            password=credentials.PASSWORD,
            measurement_codenames=list(self.codenames.values()),
        )
        self.db_logger.start()
        LOGGER.info('Logger started')

        # Each value is measured about every 5 sec, so sane interval about 2
        live_name = '{}_{}_{}_live'
        live_codenames = list(self.codenames.values()) + [name+'_inhibit' for name in list(self.codenames.values())]
        self.live_socket = LiveSocket(
            name=live_name.format(self.user, floor, vortex_number),
            codenames=live_codenames,
            internal_data_pull_socket_port = 8000 + vortex_number,
        )
        self.live_socket.start()
        LOGGER.info('Live socket started')

        # Start driver
        self.vortex = Vortex(port, slave_address)
        LOGGER.info('Vortex driver opened')

        # Init database connection
        ###self.db_connection = MySQLdb.connect(
        ###    host=credentials.HOST, user=credentials.USERNAME,
        ###    passwd=credentials.PASSWORD, db=credentials.DB)
        ###self.db_cursor = self.db_connection.cursor()

        # Initiate static information. All information about the except for
        # the list of their numbers are placed in dicts because the numbering
        # starts at 1.
        # Detector numbers: [1, 2, 3, ..., 12]
        self.detector_numbers = \
            range(1, self.vortex.get_number_installed_detectors() + 1)
        self.detector_info = \
            {detector_num: self.vortex.detector_configuration(detector_num)
             for detector_num in self.detector_numbers}
        # trip_levels are the differences that are required to force a log
        # The levels are set to 2 * the communication resolution
        # (1000 values over the full range)
        # NOTE. Since we have had a lot of noise on the CO channels, we
        # increased the level to info.range * 7.0 / 1000.0 for those
        #self.trip_levels = {detector_num: info.range * 2.0 / 1000.0 for
        #                    detector_num, info in self.detector_info.items()}
        self.trip_levels = {}
        for detector_number, info in self.detector_info.items():
            if info.unit == "PPM":
                self.trip_levels[detector_number] = info.range * 7.0 / 1000.0
            else:
                self.trip_levels[detector_number] = info.range * 2.0 / 1000.0


        # Initiate last measured values and their corresponding times
        self.detector_levels_last_values = \
            {detector_num: - (10 ** 9)
             for detector_num in self.detector_numbers}
        self.detector_levels_last_times = \
            {detector_num: 0 for detector_num in self.detector_numbers}
        self.detector_status_last_values = \
            {detector_num: {'inhibit': False, 'status': ['OK'],
                            'codename': self.detector_info[detector_num].identity}
             for detector_num in self.detector_numbers}
        self.detector_status_last_times = \
            {detector_num: 0 for detector_num in self.detector_numbers}

        # Initiate variables for system power status
        self.central_power_status_last_value = 'OK'
        self.central_power_status_last_time = - (10 ** 9)

        # Initiate variables for system status
        self.central_status_last_value = ['All OK']
        self.central_status_last_time = 0

    def close(self):
        """Close the logger and the connection to the Vortex"""
        self.db_logger.stop()
        LOGGER.info('Logger stopped')
        self.live_socket.stop()
        LOGGER.info('Live socket stopped')
        self.vortex.close()
        LOGGER.info('Vortex driver closed')

    ###@staticmethod
    ###def identity_to_codename(identity):
    ###    """Convert the identity the sensor returns to the codename used in the
    ###    database
    ###    """
    ###    # NOTE The identities was changed at some point, which is the reason where there
    ###    # is this manual mingling with name. The current names are:
    ###    # 'CO 51', 'H2 51', 'CO 55', 'H2 55', 'CO 59', 'H2 61', 'CO 61', 'H2 61',
    ###    # 'CO 42/43', 'H2 2 sal', 'CO 932', 'H2 932'
    ###    # and they need to be changed to the codenames in codenames (in __init__)

    ###    #first, second = identity.split(' ', 1)
    ###    #if len(second) == 2:
    ###    #    second = '0' + second
    ###    #identity = first + ' ' + second

    ###    #identity = identity.replace('2 sal', '2sal').replace(' ', '_').replace('/', '-')
    ###    identity = identity.replace(' ', '_').replace('/', '-')
    ###    return 'B307_gasalarm_{}'.format(identity)

    def main(self):
        """Main monitoring and logging loop"""
        # Each iteration takes about 5 sec
        while True:
            # Log detectors
            for detector_num in self.codenames.keys():
                self.log_detector(detector_num)

            # Log Vortex unit status (force log every 24 hours)
            self.log_central_unit()

    def log_detector(self, detector_num):
        """Get the levels from one detector and log if required"""
        # Get detector info and levels for this detector
        conf = self.detector_info[detector_num]
        #codename = self.identity_to_codename(conf.identity)
        codename = self.codenames[detector_num]

        LOGGER.debug('Use detector {} \'{}\''.format(detector_num, codename))
        levels = self.vortex.get_detector_levels(detector_num)
        LOGGER.debug('Levels read: {}'.format(levels))

        # Detector level
        now = time.time()
        # Always send to live socket
        self.live_socket.set_point_now(codename, levels.level)
        self.live_socket.set_point_now(codename+'_inhibit', levels.inhibit)
        # Force log every 10 m
        time_condition = \
            now - self.detector_levels_last_times[detector_num] > 600
        value_condition = \
            abs(self.detector_levels_last_values[detector_num] - levels.level)\
            >= self.trip_levels[detector_num]
        if time_condition or value_condition:
            LOGGER.debug('Send level to db trigged in time: {} or value: '
                         '{}'.format(time_condition, value_condition))
            ###self.db_logger.enqueue_point(codename, (now, levels.level))
            self.db_logger.save_point_now(codename, levels.level)
            # Update last values
            self.detector_levels_last_values[detector_num] = levels.level
            self.detector_levels_last_times[detector_num] = now
        else:
            LOGGER.debug('Level logging condition false')

        self.log_detector_status(detector_num, levels, conf)

    def log_detector_status(self, detector_num, levels, conf):
        """Sub function to log single detector status"""
        now = time.time()
        # Force log every 24 hours
        time_condition = \
            now - self.detector_status_last_times[detector_num] > 86400
        status = {'inhibit': levels.inhibit, 'status': levels.status,
                  'codename': conf.identity}

        ##### HACK HACK HACK FIXME There is a duplicate name error in the configuration
        #if detector_num == 6 and status['codename'] == 'H2 61':
        #    status['codename'] = 'H2 59'
        ##### HACK HACK HACK FIXME

        value_condition = \
            (status != self.detector_status_last_values[detector_num])

        # Check if we should log
        if time_condition or value_condition:
            check_in = time_condition and not value_condition
            LOGGER.info('Send detector status to db trigged on time: {} or '
                        'value: {}'.format(time_condition, value_condition))
            query = 'INSERT INTO status_{} '\
                '(time, device, status, check_in, central, floor) '\
                'VALUES (FROM_UNIXTIME(%s), %s, %s, %s, %s, %s);'.format(self.user)
            values = (now, detector_num, json.dumps(status), check_in, self.vortex_number, self.floor)
            self._wake_mysql()
            self.db_logger.cursor.execute(query, values)
            # Update last values
            self.detector_status_last_times[detector_num] = now
            self.detector_status_last_values[detector_num] = status
        else:
            LOGGER.debug('Detector status logging condition false')

    def log_central_unit(self):
        """Log the status of the central unit"""
        power_status = self.vortex.get_system_power_status().value
        now = time.time()
        # Force a log once per 24 hours
        time_condition = now - self.central_power_status_last_time > 86400
        value_condition = self.central_power_status_last_value != power_status
        LOGGER.debug('Read central power status: \'{}\''.format(power_status))
        if time_condition or value_condition:
            check_in = time_condition and not value_condition
            LOGGER.info('Send power status to db trigged in time: {} or '
                        'value: {}'.format(time_condition, value_condition))
            query = 'INSERT INTO status_{} '\
                '(time, device, status, check_in, central, floor) '\
                'VALUES (FROM_UNIXTIME(%s), %s, %s, %s, %s, %s);'.format(self.user)
            values = (now, 255, json.dumps(power_status), check_in, self.vortex_number, self.floor)
            self._wake_mysql()
            self.db_logger.cursor.execute(query, values)
            # Update last values
            self.central_power_status_last_time = now
            self.central_power_status_last_value = power_status
        else:
            LOGGER.debug('Power status logging condition false')

        self.log_central_unit_generel()

    def log_central_unit_generel(self):
        """Log the generel status from the central"""
        generel_status = self.vortex.get_system_status()
        now = time.time()
        # Force a log once per 24 hours
        time_condition = now - self.central_status_last_time > 86400
        value_condition = generel_status != self.central_status_last_value
        LOGGER.debug(
            'Read central generel status: \'{}\''.format(generel_status))
        if time_condition or value_condition:
            check_in = time_condition and not value_condition
            LOGGER.info('Send central generel status to db trigged in time: {}'
                        ' or value: {}'.format(time_condition,
                                               value_condition))
            query = 'INSERT INTO status_{} '\
                '(time, device, status, check_in, central, floor) '\
                'VALUES (FROM_UNIXTIME(%s), %s, %s, %s, %s, %s);'.format(self.user)
            values = (now, 254, json.dumps(generel_status), check_in, self.vortex_number, self.floor)
            self._wake_mysql()
            self.db_logger.cursor.execute(query, values)
            # Update last values
            self.central_status_last_time = now
            self.central_status_last_value = generel_status
        else:
            LOGGER.debug('Central generel status logging confition false')

    def _wake_mysql(self):
        """Send a ping via the connection and re-initialize the cursor"""
        # This should prevent an OperationalError(MySQL server has gone away) after 24 hours
        self.db_logger.connection.ping(True)
        self.db_logger.cursor = self.db_logger.connection.cursor()
