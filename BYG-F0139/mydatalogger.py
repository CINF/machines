# -*- coding: utf-8 -*-
# !/usr/bin/env python
# pylint: disable=C0301,R0904, C0103
""" Pressure and temperature logger """

from __future__ import print_function

import sys
sys.path.insert(1, '/home/pi/PyExpLabSys')
#sys.path.insert(2, '../..')

import threading
import time
import logging
from PyExpLabSys.common.loggers import ContinuousLogger


from PyExpLabSys.common.sockets import DateDataPullSocket
#from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
#from PyExpLabSys.auxiliary.pid import PID
import PyExpLabSys.drivers.omega_cni as omega_CNi32
#import PyExpLabSys.drivers.kampstrup as kampstrup

import pykamtest

import socketinfo
import credentials
ContinuousLogger.host = credentials.dbhost
ContinuousLogger.database = credentials.dbname


class RunningMean(object):
    def __init__(length):
        self.list = list(length)

class WaterTemperatureReader(threading.Thread):
    """ Temperature reader """
    def __init__(self,):
        threading.Thread.__init__(self)
        self.chlist = {'tabs_guard_temperature_inlet': 0,
                   'tabs_guard_temperature_outlet': 1,
                   'tabs_guard_temperature_delta': 2,
                   'tabs_floor_temperature_inlet': 3,
                   'tabs_floor_temperature_outlet': 4,
                   'tabs_floor_temperature_delta': 5,                   
                   'tabs_ceiling_temperature_inlet': 6,
                   'tabs_ceiling_temperature_outlet': 7,
                   'tabs_ceiling_temperature_delta': 8,
                   'tabs_guard_water_flow': 9,
                   'tabs_floor_water_flow': 10,
                   'tabs_ceiling_water_flow': 11,}
        self.DATA= {}
        for key in self.chlist.keys():
            self.DATA[key] = None
        port = '/dev/serial/by-id/usb-Silicon_Labs_Kamstrup_M-Bus_Master_MultiPort_250D_131751521-if00-port0'
        self.MCID = {}
        self.MCID['tabs_guard_'] = 13
        self.MCID['tabs_floor_'] = 15
        self.MCID['tabs_ceiling_'] = 14
        
        self.MC302device = pykamtest.kamstrup(serial_port=port)

        self.quit = False
        self.ttl = 500



    def value(self, channel):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel in self.chlist.values():
                for key, value in self.chlist.items():
                    if channel == value:
                        return_val = self.DATA[key]
            else:
                return_val = None
        return return_val

    def update_values(self,):
        for key, ID in self.MCID.items():
            try:
                v = self.MC302device.read_water_temperature(ID)
                #print(v)
                if len(v) == 4:
                    self.DATA[key +'temperature_inlet'] = v['inlet']
                    self.DATA[key +'temperature_outlet'] = v['outlet']
                    self.DATA[key +'temperature_delta'] = v['diff']
                    self.DATA[key +'water_flow'] = v['flow']
                else:
                    self.DATA[key +'temperature_inlet'] = None
                    self.DATA[key +'temperature_outlet'] = None
                    self.DATA[key +'temperature_delta'] = None
                    self.DATA[key +'water_flow'] = None
                self.ttl = 500
            except IndexError:
                print("av")
            except ValueError, TypeError:
                self.DATA[key +'temperature_inlet'] = None
                self.DATA[key +'temperature_outlet'] = None
                self.DATA[key +'temperature_delta'] = None
                self.DATA[key +'water_flow'] = None
            time.sleep(2)
            #print(self.temperatures)

    def run(self):
        while not self.quit:
            self.update_values()
            time.sleep(2)
        self.quit = True
            
    def stop(self,):
        self.quit = True
        self.MC302device.close()

class TemperatureReader(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
        threading.Thread.__init__(self)
        self.SYSTEMS = {}
        for sy in ['tabs_guard', 'tabs_floor', 'tabs_ceiling', 'tabs_cooling', 'tabs_ice']:
            self.SYSTEMS[sy] = {'temperature_inlet': None, # float in C
                                'temperature_outlet': None, # float in C
                                'temperature_setpoint': None, # float in C
                                'valve_cooling': None, # float 0-1
                                'valve_heating': None, # float 0-1
                                'pid_value': None, # float -1-1
                                'water_flow': None} # float in l/min
        self.OmegaPortsDict = {}
        self.OmegaPortsDict['tabs_guard_temperature_inlet'] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWEA5HJ-if00-port0'
        self.OmegaPortsDict['tabs_floor_temperature_inlet'] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTYIWHC9-if00-port0'
        self.OmegaPortsDict['tabs_ceiling_temperature_inlet'] = '/dev/serial/by-id/usb-OMEGA_ENGINEERING_12.34-if00'
        self.OmegaPortsDict['tabs_cooling_temperature_inlet'] = '/dev/serial/by-id/usb-OMEGA_ENGINEERING_12.34-if01'
        
        #self.OmegaPortsDict['tabs_guard_temperature_inlet'] = '/dev/ttyUSB1'
        #self.OmegaPortsDict['tabs_floor_temperature_inlet'] = '/dev/ttyUSB0'
        self.OmegaPortsDict['tabs_ceiling_temperature_inlet'] = '/dev/ttyACM3'
        self.OmegaPortsDict['tabs_cooling_temperature_inlet'] = '/dev/ttyACM2'
        
        self.OmegaCommStnd = {}
        self.OmegaCommStnd['tabs_guard_temperature_inlet'] = 'rs485'
        self.OmegaCommStnd['tabs_floor_temperature_inlet'] = 'rs485' #add 2
        self.OmegaCommStnd['tabs_ceiling_temperature_inlet'] = 'rs232'
        self.OmegaCommStnd['tabs_cooling_temperature_inlet'] = 'rs232'
        
        self.OldValue = {}
        self.OldValue['tabs_guard_temperature_inlet'] = None
        self.OldValue['tabs_floor_temperature_inlet'] = None
        self.OldValue['tabs_ceiling_temperature_inlet'] = None
        self.OldValue['tabs_cooling_temperature_inlet'] = None
        
        self.OffSet = {}
        self.OffSet['tabs_guard_temperature_inlet'] = 0.62
        self.OffSet['tabs_floor_temperature_inlet'] = 1.32
        self.OffSet['tabs_ceiling_temperature_inlet'] = 0.30
        self.OffSet['tabs_cooling_temperature_inlet'] = -0.49
        
        self.OmegaCommAdd = {}
        self.OmegaCommAdd['tabs_guard_temperature_inlet'] = 1
        self.OmegaCommAdd['tabs_floor_temperature_inlet'] = 1
        
        self.OmegaDict = {}
        for key in codenames:
            #print('Initializing: ' + key)
            self.OmegaDict[key] = omega_CNi32.ISeries(self.OmegaPortsDict[key], 9600, comm_stnd=self.OmegaCommStnd[key])
            
        #self.temperatures = {'tabs_guard_temperature': None,
        #                     'tabs_floor_temperature': None,
        #                     'tabs_ceiling_temperature': None,
        #                     'tabs_cooling_temperature': None}
        self.quit = False
        self.ttl = 20

    def setup_rtd(self, name):
        #print('Format: ' + str(value.command('R08') ) )
        print('Intup Type: ' + self.OmegaDict[name].command('R07'))
        print('Reading conf: ' + self.OmegaDict[name].command('R08'))
        if name == 'tabs_guard_temperature_inlet':
            pass
        elif name == 'tabs_floor_temperature_inlet':
            pass
        elif name == 'tabs_ceiling_temperature_inlet':
            #self.OmegaDict[name].command('W0701')
            #self.OmegaDict[name].reset_device()
            pass
        elif name == 'tabs_cooling_temperature_inlet':
            
            pass

    def value(self, channel):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            me = 'temperature_inlet'
            if channel == 0:
                sy = 'tabs_guard'
                return_val = self.SYSTEMS[sy][me]
            elif channel == 1:
                sy = 'tabs_floor'
                return_val = self.SYSTEMS[sy][me]
            elif channel == 2:
                sy = 'tabs_ceiling'
                return_val = self.SYSTEMS[sy][me]
            elif channel == 3:
                sy = 'tabs_cooling'
                return_val = self.SYSTEMS[sy][me]
        return return_val

    def update_values(self,):
        for key, value in self.OmegaDict.items():
            _key = str(key).rsplit('_')
            sy = _key[0]+'_' + _key[1]
            me = _key[2]+'_' + _key[3]
            #print(sy, me)
            try:
                #print("Omega: {}".format(key))
                if self.OmegaCommStnd[key] == 'rs485':
                    v = value.read_temperature(address=self.OmegaCommAdd[key])
                    #print('Temp: ' + str(self.temperatures[key]) )
                elif self.OmegaCommStnd[key] == 'rs232':
                    v = value.read_temperature()
                    #print('Temp: ' + str(self.temperatures[key]) )
                    #print('Format: ' + str(value.command('R08') ) )
                else:
                    self.SYSTEMS[sy][me] = None
                if type(v) == type(0.0):
                    new_val = v + self.OffSet[key]
                old_val = self.OldValue[key]
                if new_val == None:
                    pass
                elif old_val == None:
                    old_val = new_val
                    self.SYSTEMS[sy][me] = new_val
                elif abs(new_val - old_val) < 0.5:
                    old_val = new_val
                    self.SYSTEMS[sy][me] = new_val
                else:
                    pass
                self.ttl = 50
            except IndexError:
                print("av")
            except ValueError, TypeError:
                self.SYSTEMS[sy][me] = None
        #print(self.temperatures)

    def run(self):
        while not self.quit:
            time.sleep(2)
            self.update_values()
            
    def stop(self,):
        self.quit = True
        for key, value in self.OmegaDict.items():
            value.close()

#logging.basicConfig(filename="logger.txt", level=logging.ERROR)
#logging.basicConfig(level=logging.ERROR)


class MainDatalogger(threading.Thread):
    """ Temperature reader """
    def __init__(self,):
        threading.Thread.__init__(self)
        #from datalogger import TemperatureReader
        self.quit = False
        self.codenames = ['tabs_guard_temperature_inlet',
                     'tabs_floor_temperature_inlet',
                     'tabs_ceiling_temperature_inlet',
                     'tabs_cooling_temperature_inlet',
                     ]
        self.MC302 = WaterTemperatureReader()
        self.MC302.start()
        self.codenames = [
                     'tabs_cooling_temperature_inlet',
                     ]
        self.omega_temperature = TemperatureReader(['tabs_cooling_temperature_inlet',])
        self.omega_temperature.daemon = True
        self.omega_temperature.start()
        #omega_temperature.update_values()
        
        time.sleep(1.5)
        
        chlist = {'tabs_guard_temperature_inlet': 0,
                  'tabs_floor_temperature_inlet': 1,
                  'tabs_ceiling_temperature_inlet': 2,
                  'tabs_cooling_temperature_inlet': 3}
        self.loggers = {}
        for key in ['tabs_cooling_temperature_inlet',]:
            self.loggers[key] = ValueLogger(self.omega_temperature, comp_val = 0.2, maximumtime=300,
                                            comp_type = 'lin', channel = chlist[key])
            self.loggers[key].start()
        chlist = {'tabs_guard_temperature_inlet': 0,
                   'tabs_guard_temperature_outlet': 1,
                   'tabs_guard_temperature_delta': 2,
                   'tabs_floor_temperature_inlet': 3,
                   'tabs_floor_temperature_outlet': 4,
                   'tabs_floor_temperature_delta': 5,                   
                   'tabs_ceiling_temperature_inlet': 6,
                   'tabs_ceiling_temperature_outlet': 7,
                   'tabs_ceiling_temperature_delta': 8,
                   'tabs_guard_water_flow': 9,
                   'tabs_floor_water_flow': 10,
                   'tabs_ceiling_water_flow': 11,}
        for key in chlist.keys():
            self.loggers[ key] = ValueLogger(self.MC302, comp_val = 0.2, maximumtime=300,
                                            comp_type = 'lin', channel = chlist[key])
            self.loggers[key].start()
        self.codenames = chlist.keys()+ ['tabs_cooling_temperature_inlet']
        #livesocket = LiveSocket('tabs_temperature_logger', codenames, 2)
        #livesocket.start()
        sockname = 'tabs_temperatures'
        self.PullSocket = DateDataPullSocket(sockname, self.codenames, timeouts=[60.0]*len(self.codenames), port = socketinfo.INFO[sockname]['port'])
        self.PullSocket.start()
        
        self.db_logger = ContinuousLogger(table='dateplots_tabs', username=credentials.user, password=credentials.passwd, measurement_codenames=self.codenames)
        self.db_logger.start()
    
    def run(self,):
        i = 0
        while not self.quit and self.omega_temperature.isAlive():
            try:
                #print(i)
                time.sleep(1)
                for name in self.loggers.keys():
                    v = self.loggers[name].read_value()
                    #livesocket.set_point_now(name, v)
                    self.PullSocket.set_point_now(name, v)
                    
                    if self.loggers[name].read_trigged():
                        if __name__ == '__main__':
                            print('Log: ', i, name, v)
                        self.db_logger.enqueue_point_now(name, v)
                        self.loggers[name].clear_trigged()
                    else:
                        if __name__ == '__main__':
                            print('STA: ', i, name, v)
            except (KeyboardInterrupt, SystemExit):
                pass
                #self.omega_temperature.close()
                #report error and proceed
            i += 1
        self.stop()
        
    def stop(self):
        self.quit = True
        self.omega_temperature.stop()
        self.MC302.stop()
        self.db_logger.stop()
        self.PullSocket.stop()
        for key in self.codenames:
            self.loggers[key].status['quit'] = True

if __name__ == '__main__':
    MDL = MainDatalogger()
    time.sleep(3)
    MDL.start()
    
    while MDL.isAlive():
        try:
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            MDL.quit = True
    #print('END')
    
