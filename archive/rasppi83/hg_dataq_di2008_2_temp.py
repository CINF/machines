import serial
import time
import threading
import datetime
import curses
import credentials
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.value_logger import LoggingCriteriumChecker
import numpy as np

class DI2008(object):

    def __init__(self, port='/dev/ttyACM0'):
        self.ser = serial.Serial(port=port,
                                 baudrate=115200,
                                 timeout=0.1)
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
                   'T': [0.009155, 100]}
        self.channel = {i: None for i in range(8)}
        self.read_cjc_offsets()

    def comm(self, command, timeout=1):
        self.ser.write((command+'\r').encode())
        if not self.acquiring:
            time.sleep(.1)
            t0 = time.time()
            while True:
                if time.time() - t0 > timeout:
                    return 'Timeout'
                if self.ser.inWaiting() > 0:
                    while True:
                        try:
                            s = self.ser.readline().decode()
                            s = s.strip('\n\r\0')
                            break
                        except:
                            continue
                    if s != "":
                        print(repr(s))
                        return s.lstrip(command).strip()

    def config_scan_list(self):
        """Configure channels 0–6 as K-type thermocouples, 7 as voltage ±25 mV"""
    def config_scan_list(self):
        self.stop()
        print('Configuring full 8-channel scan list...')
        self.comm('slist 0 4864')
        self.comm('slist 1 4865')
        self.comm('slist 2 4866')
        self.comm('slist 3 4867')
        self.comm('slist 4 4868')
        self.comm('slist 5 4869')
        self.comm('slist 6 4870')
        self.comm('slist 7 1031') #1031 25mv
        self.decimation_factor('10')
        self.comm('filter * 1')
        self.srate(4)
        self.packet_size(0)
        print('Full scan list set!')


    def stop(self):
        self.ser.write('stop\r'.encode())
        print('Stop', self.ser.inWaiting())
        self.acquiring = False
        self.comm('stop')

    def packet_size(self, value):
        if value not in range(4):
            raise ValueError('Value must be 0, 1, 2, or 3.')
        psdict = {0: 16, 1: 32, 2: 64, 3: 128}
        self.ps = psdict[value]
        print('Packet size: {} B'.format(self.ps))
        self.comm('ps ' + str(value))

    def decimation_factor(self, value):
        value = int(value)
        if 1 <= value <= 32767:
            self.comm('dec ' + str(value))
            self.dec = value
        else:
            raise ValueError('DEC out of range')

    def srate(self, value):
        value = int(value)
        if 4 <= value <= 2232:
            self.comm('srate ' + str(value))
            self.sr = value
        else:
            raise ValueError('SRATE out of range')

    def start(self):
        self._flush()
        self.acquiring = True
        self.pointer = 0
        self.ser.write('start 1\r'.encode())

    def _flush(self):
        print('Flushing: ' + repr(self.ser.read(self.ser.inWaiting())))

    def read(self):
        if not self.acquiring:
            return

        # Wait until we have a full packet
        while self.ser.inWaiting() < self.ps:
            time.sleep(0.01)

        # Read exactly one full packet
        data = self.ser.read(self.ps)
        if len(data) != self.ps:
            self.error = 'Incomplete packet'
            return



        for i in range(8):
            raw = data[2*i : 2*i+2]
            result = int.from_bytes(raw, byteorder='little', signed=True)

            if result == 32767:
                self.channel[i] = 'cjc error'
            elif result == -32768:
                self.channel[i] = 'open'
            else:
                if i < 7:
                    # Channels 0–6: thermocouple
                    param = self.tc['K']
                    self.channel[i] = param[0] * result + param[1]
                else:
                    # Channel 7: voltage ±25 mV
                    voltage_mV = (result / 32768.0) * 25.0
                    self.channel[i] = voltage_mV


    def read_cjc_offsets(self):
        coefficient = 0.0625
        values = self.comm('cjcdelta -1').split(' ')
        self.cjc = [float(i) * coefficient for i in values]

class Reader(threading.Thread):

    def __init__(self, driver, codenames, live_socket, database_saver, criterium_checker):
        threading.Thread.__init__(self)
        self.dev = driver
        self.codenames = codenames
        self.live_socket = live_socket
        self.db_saver = database_saver
        self.crit_check = criterium_checker
        self.daemon = True
        self.mass = np.array([np.nan]*5)
        self.t = 0

    def stop(self):
        self.dev.stop()

    def run(self):
        self.dev.config_scan_list()
        self.dev.start()
        t0 = time.time()
        while time.time() - t0 < 5:
            self.dev.read()
        while self.dev.acquiring:
            t = time.time()
            self.dev.read()
            self.t = time.time() - t
            for i in range(8):
                value = self.dev.channel[i]
                if i == 7: # weight cell convert to kg
                    #value = value / 4.1 * 0.45359237 * 200
                    #value = value
                    value = (value + 0.6908) / 0.2320 # from data gathered on July 31 2025

                self.live_socket.set_point_now(self.codenames[i], value)
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
        self.screen = curses.initscr()
        self.win = curses.newwin(20, 60, 0, 0)
        curses.cbreak()
        curses.noecho()
        curses.halfdelay(10)
        print('Reader initialized')

    def stop(self):
        self.printing = False
        self.reader.stop()
        time.sleep(1)
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
                self.print_data()
            except KeyboardInterrupt:
                self.stop()

    def print_data(self):
        self.win.addstr(0, 0, 'DataQ DI-2008 monitor')
        self.win.addstr(1, 4, '(Quit with "q")')
        self.win.addstr(3, 0, 'Time: {}   '.format(datetime.datetime.now()))
        self.win.addstr(4, 0, 'Bytes in waiting: {}   '.format(self.dev.ser.inWaiting()))
        self.win.addstr(5, 0, 'Error: {}'.format(self.dev.error))
        self.win.addstr(7, 0, 'Channels')
        for i in range(8):
            #print('smarf: channel: ', self.dev.channel[i])
            channel = self.dev.channel[i]
            if i == 7:
                try:
                    #self.win.addstr(8+i, 0, '{}: {:.3f} kg                  '.format(i+1, channel / 4.1 * 0.45359237 * 200))
                    #self.win.addstr(8+i, 0, '{}: {:.3f} kg                  '.format(i+1, channel))
                    self.win.addstr(8+i, 0, '{}: {:.3f} kg                  '.format(i+1, (channel + 0.6908) / 0.2320))
                except (TypeError, ValueError, curses.error):
                    self.win.addstr(8+i, 0, '{}: invalid data               '.format(i+1))
            else:
                cjc = self.dev.cjc[i]
                if isinstance(channel, str):
                    formatstring = '{}: {}      ({:.3f} C)     '
                else:
                    formatstring = '{}: {:.3f} C  ({:.3f} C)     '
                try:
                    self.win.addstr(8+i, 0, formatstring.format(i+1, channel, cjc))
                except (TypeError, ValueError, curses.error):
                    self.win.addstr(8+i, 0, '{}: invalid data               '.format(i+1))
        self.win.addstr(17, 0, 'Loop timer: {:.3f}s     '.format(self.reader.t))
        self.win.refresh()

if __name__ == '__main__':
    path = '/dev/serial/by-id/usb-DATAQ_Instruments_Generic_Bulk_Device_00000000_DI-2008-if00'
    dev = DI2008(port=path)
    time.sleep(1)
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
    database_saver = ContinuousDataSaver('dateplots_omicron', credentials.user, credentials.passwd, codenames)
    database_saver.start()
    
    criterium_checker = LoggingCriteriumChecker(
        codenames=codenames,
        types=['lin']*len(codenames),
        criteria=[0.5]*len(codenames),
        time_outs=[300, 300, 300, 300, 300, 300, 300, 5], #hrogr can update, below 380 ms
    )
    
    reader = Reader(dev, codenames, live_socket, database_saver, criterium_checker)
    reader.start()
    time.sleep(5)
    printer = Printer(reader)
    printer.start()
