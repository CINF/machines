import serial
import time
import threading
from PyExpLabSys.common.sockets import LiveSocket#, DateDataPullSocket
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.value_logger import LoggingCriteriumChecker

class DI2008(object):

    def __init__(self, port='/dev/ttyACM0'):
        self.ser = serial.Serial(port=port,
                                 baudrate=115200,
                                 timeout=0.1,
        )
        self.acquiring = False
        self.stop()
        self.ps = None
        self.error = 'None'
        print('DI 2008 initialized')
        self.tc = {'B': [0.023956, 1035],
                   'E': [0.018311, 400],
                   'J': [0.021515, 495],
                   'K': [0.023987, 586],
                   'N': [0.022888, 550],
                   'R': [0.02774, 859],
                   'S': [0.02774, 859],
                   'T': [0.009155, 100]
        }
        self.channel = {
            0: None,
            1: None,
            2: None,
            3: None,
            4: None,
            5: None,
            6: None,
            7: None,
        }
        self.read_cjc_offsets()


    def comm(self, command, timeout=1):
        #self._flush()
        self.ser.write((command+'\r').encode())
        if not self.acquiring:
            time.sleep(.1)
            # Echo commands if not acquiring
            t0 = time.time()
            while True:
                if time.time() - t0 > timeout:
                    return 'Timeout'
                if self.ser.inWaiting() > 0:
                    while True:
                        try:
                            s = self.ser.readline().decode()
                            s = s.strip('\n')
                            s = s.strip('\r')
                            s = s.strip(chr(0))
                            print(repr(s))
                            break
                        except:
                            continue
                    if s != "":
                        print(s)
                        return s.lstrip(command).strip()

    def config_scan_list(self):
        """FIXME
        Configure channels"""
        self.comm('slist 0 4864') # K-type TC on channel 0
        self.comm('slist 1 4865') # K-type TC on channel 1
        self.comm('slist 2 4866') # K-type TC on channel 2
        self.comm('slist 3 4867') # K-type TC on channel 3
        self.comm('slist 4 4868') # K-type TC on channel 4
        self.comm('slist 5 4869') # K-type TC on channel 5
        self.comm('slist 6 4870') # K-type TC on channel 6 ###
        #self.comm('slist 7 4871') # K-type TC on channel 7 ###
        self.comm('slist 7 1031') # +- 25mV input
        self.decimation_factor('10') # decimation factor: 10 acquisitions
        self.comm('filter * 1') # filter mode: average on all channels
        self.srate(4) # fastest sample rate
        self.packet_size(0) # packets of 16 bytes

    def stop(self):
        self.ser.write('stop\r'.encode())
        print('Stop', self.ser.inWaiting())
        #self.ser.write('stop\r'.encode())
        #print('Stop', self.ser.inWaiting())
        self.acquiring = False
        self.comm('stop')


    def packet_size(self, value):
        if value not in range(4):
            raise ValueError('Value must be 0, 1, 2, or 3.')
        psdict = {0: 16, 1: 32, 2: 64, 3: 128}
        self.ps = psdict[value] # Packet size [bytes]
        print('Packet size: {} B'.format(self.ps))
        self.comm('ps ' + str(value))

    def get_sample_rate(self):
        srate = int(self.comm('info 9'))
        self.sample_rate = srate / (self.sr * self.dec)
        print('Sample rate: ', self.sample_rate, ' Hz')

    def set_sample_rate(self):
        pass #NOTIMPLEMENTED

    def decimation_factor(self, value):
        value = int(value)
        if value >= 1 and value <= 32767:
            self.comm('dec ' + str(value))
            self.dec = value
        else:
            raise ValueError('Value DEC out of range')

    def srate(self, value):
        value = int(value)
        if value >= 4 and value <= 2232:
            self.comm('srate ' + str(value))
            self.sr = value
        else:
            raise ValueError('Value SRATE out of range')

    def start(self):
        self._flush()
        self.acquiring = True
        self.pointer = 0
        self.ser.write('start 1\r'.encode())

    def print_values(self):
        print('{:3.1f}'.format(time.time()-self.t0), end='')
        for i in range(8):
            print(' {} K   '.format(self.channel[i]), end='')
        print('                                          ', end='\r')
        
    def _flush(self):
        print('Flushing: ' + repr(self.ser.read(self.ser.inWaiting())))
        
    def read(self):
        if not self.acquiring:
            return
        while dev.ser.inWaiting() == 0:
            time.sleep(0.05)
        for i in range(int(dev.ps/2)):
            byte = dev.ser.read(2)
            if b'stop 01' in byte:
                self.acquiring = False
                self.error = 'Buffer overflow'
                return
            result = int.from_bytes(byte, byteorder='little', signed=True)
            if result == 32767:
                result = 'cjc error'
                self.channel[self.pointer] = result
            elif result == -32768:
                result = 'open'
                self.channel[self.pointer] = result
            else:
                try:
                    param = self.tc['K']
                    self.channel[self.pointer] = param[0] * result + param[1]
                except KeyError:
                    raise ValueError('tc_type must be a valid thermocouple type!')
            self.pointer = (self.pointer + 1) % 8

    def read_cjc_offsets(self):
        coefficient = 0.0625 # deg C
        values = self.comm('cjcdelta -1').split(' ')
        self.cjc = [float(i)*coefficient for i in values]
        

    def read_TC(self, tc_type, timeout=1):
        """Read a thermocouple byte"""
        
        t0 = time.time()
        temp = 0
        values = int(self.ps/2)
        for i in range(values):
            while self.ser.inWaiting() == 0:
                if time.time() - t0 > timeout:
                    print('TC Timeout')
                    return t0, 0
                time.sleep(1./self.sample_rate/10)
            byte = self.ser.read(2)
            result = int.from_bytes(byte, byteorder='little', signed=True)
            #print(result)
            if result == 32767:
                result = 'cjc error'
            elif result == -32768:
                result = 'open'
            else:
                try:
                    param = self.tc[tc_type]
                except KeyError:
                    raise ValueError('tc_type must be a valid thermocouple type!')
                temp += param[0] * result + param[1]
        temp /= values
        #print(t0, temp, param[1])
        return t0, temp

import datetime
import threading
import curses
import credentials

class Reader(threading.Thread):

    def __init__(self, driver, codenames, live_socket, database_saver, criterium_checker):
        threading.Thread.__init__(self)
        self.dev = driver
        self.codenames = codenames
        self.live_socket = live_socket
        self.db_saver = database_saver
        self.crit_check = criterium_checker
        self.daemon = True

    def stop(self):
        self.dev.stop()
        
    def run(self):
        self.dev.config_scan_list()
        self.dev.start()
        t0 = time.time()
        while time.time() - t0 < 5:
            self.dev.read()
        while self.dev.acquiring:
            self.dev.read()
            for i in range(8):
                value = self.dev.channel[i]
                live_socket.set_point_now(self.codenames[i], value)
                if isinstance(value, float):
                    if self.crit_check.check(self.codenames[i], value):
                        self.db_saver.save_point_now(self.codenames[i], value)

class Printer(threading.Thread):

    def __init__(self, reader):
        threading.Thread.__init__(self)
        self.daemon = False
        self.reader = reader
        self.dev = self.reader.dev
        self.printing = True

        # Init curses
        self.screen = curses.initscr()
        self.win = curses.newwin(20, 60, 0, 0)
        curses.cbreak()
        curses.noecho()
        curses.halfdelay(10)
        print('Reader initialized')

    def stop(self):
        """Exit nicely"""
        self.printing = False
        self.reader.stop()
        time.sleep(1)
        #self.screen.keypad(0)
        curses.nocbreak()
        curses.echo()
        curses.endwin()
        time.sleep(1)
        
    def run(self):
        while self.printing:
            try:
                char = self.screen.getch()
                if char == ord('q'):
                    self.stop()
                #time.sleep(1)
                self.print_data()
            except KeyboardInterrupt:
                self.stop()

    def print_data(self):
        # Print header
        self.win.addstr(0, 0, 'DataQ DI-2008 monitor')
        self.win.addstr(1, 4, '(Quit with "q")')

        # Print auxiliary data
        self.win.addstr(3, 0, 'Time: {}   '.format(datetime.datetime.now()))
        self.win.addstr(4, 0, 'Bytes in waiting: {}   '.format(self.dev.ser.inWaiting()))
        self.win.addstr(5, 0, 'Error: {}'.format(self.dev.error))

        # Print main data
        self.win.addstr(7, 0, 'Channels')
        for i in range(8):
            channel = self.dev.channel[i]
            cjc = self.dev.cjc[i]
            if isinstance(channel, str):
                formatstring = '{}: {}      ({:.3f} C)     '
            else:
                formatstring = '{}: {:.3f} C  ({:.3f} C)     '
            try:
                self.win.addstr(8+i, 0, formatstring.format(i+1, channel, cjc))
            except curses.error:
                print(formatstring.format(i+1, channel, cjc))

        # Apply
        self.win.refresh()

if __name__ == '__main__':
    #path = '/dev/ttyACM0'
    path = '/dev/serial/by-id/usb-DATAQ_Instruments_Generic_Bulk_Device_00000000_DI-2008-if00'

    dev = DI2008(port=path)
    #dev.comm('ps 0')
    #dev.initialize()
    time.sleep(1)

    """
    def test(ps=0, tc_type='K'):
        dev.config_scan_list()
        dev.packet_size(ps)
        dev.t0 = time.time()
        pointer = 0
        dev.start()
        while True:
            #print(time.time()-t0)
            t0 = time.time()
            dev.read()
            dev.print_values()
    """
    codenames = [
        'omicron_dataq_ch1',
        'omicron_dataq_ch2',
        'omicron_dataq_ch3',
        'omicron_dataq_ch4',
        'omicron_dataq_ch5',
        'omicron_dataq_ch6',
        'omicron_dataq_ch7',
        'omicron_dataq_ch8',
    ]
    live_socket = LiveSocket('omicron_TPD_DI2008', codenames)
    live_socket.start()

    database_saver = ContinuousDataSaver(
        'dateplots_omicron', credentials.user,
        credentials.passwd, codenames,
        )
    database_saver.start()

    criterium_checker = LoggingCriteriumChecker(
        codenames=codenames,
        types=['lin']*len(codenames),
        criteria=[0.5]*len(codenames),
        time_outs=[300]*len(codenames),
        )
    
    reader = Reader(dev, codenames, live_socket, database_saver, criterium_checker)
    reader.start()

    time.sleep(5)
    
    printer = Printer(reader)
    printer.start()
    
