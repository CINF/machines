import serial
import time
import threading

class DI2008(object):

    def __init__(self, port='/dev/ttyACM0'):
        self.ser = serial.Serial(port=port,
                                 baudrate=115200,
                                 timeout=0.1,
        )
        self.acquiring = False
        self.stop()
        self.ps = None
        self.packet_size(3)
        self.config_scan_list()
        self.decimal(1)
        self.srate(4)
        print('DI 2008 initialized')
        self.get_sample_rate()
        self.tc = {'B': [0.023956, 1035],
                   'E': [0.018311, 400],
                   'J': [0.021515, 495],
                   'K': [0.023987, 586],
                   'N': [0.022888, 550],
                   'R': [0.02774, 859],
                   'S': [0.02774, 859],
                   'T': [0.009155, 100]
        }


    def comm(self, command, timeout=1):
        print('Flushing: ' + repr(self.ser.read(self.ser.inWaiting())))
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

    def decimal(self, value):
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

import pickle
class Reader(threading.Thread):

    def __init__(self, driver, window=53, order=1, tstop=4, deltat=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self.dev = driver
        self.x, self.y = [], []
        self.y_filter = []
        self.window = window
        self.order = order
        self.t_stop = tstop
        self.pickle_name = 'dataq_data_ps-{}_tint-{}_wind-{}_ord-{}.pickle'.format(self.dev.ps, deltat, window, order)
        self.pickle_name = 'lab_test_rasppi83_ps{}.pickle'.format(self.dev.ps)
        print('Reader initialized')

    def run(self, stop=4):
        self.t0 = time.time()
        self.quit = False
        self.dev.acquiring = True
        self.dev.comm('start')
        print('Starting while loop')
        while self.quit is False:
            try:
                res = self.dev.read_TC('K')
                t, T = res
            except ValueError:
                print('ValueError')
                print(res)
                print(self.dev.ser.inWaiting())
                continue
            t -= self.t0
            #try:
            #    T2 = savgol_filter(self.y + [T], self.window, self.order)[-1]
            #except:
            #    T2 = None
            print(t, T)#, T2)

            #self.x.append(t)
            #self.y.append(T)
            #self.y_filter.append(T2)
            if t > self.t_stop:
                self.quit = True
        self.dev.stop()
        print('Exiting while loop')
        self.dev.get_sample_rate()
        #pickle_data = {
        #    'time': self.x,
        #    'other': {
        #        'Raw temperature': self.y,
        #        #'Savgol temperature': self.y_filter,
        #    }
        #}
        #pickle.dump(pickle_data, open(self.pickle_name, 'wb'))

    def print_data(self):
        print(len(self.x), len(self.y), len(self.y_filter))


if __name__ == '__main__':
    #path = '/dev/ttyACM0'
    path = '/dev/serial/by-id/usb-DATAQ_Instruments_Generic_Bulk_Device_00000000_DI-2008-if00'
    
    dev = DI2008(port=path)
    #dev.comm('ps 0')
    #dev.initialize()
    time.sleep(1)
    reader = Reader(dev, window=53, order=1)
    reader.t_stop = 15
    #window, order = 53, 1
    ifdone = False
    reader.start()
    time.sleep(0.1)
    
    import numpy as np
    #from scipy.signal import savgol_filter
    
    #import matplotlib
    #matplotlib.use('GTKAgg')
    #matplotlib.use('Qt4Agg')
    #print(1)
    #import matplotlib.pyplot as plt
    #from matplotlib.animation import FuncAnimation

    #plt.style.use('fivethirtyeight')
    
    """
    counter = 0
    xy = np.zeros((1000, 2))
    print(2)
    """

    # Initialize figure
    #fig, ax = plt.subplots(1, 1)
    #ax.set_aspect('equal')
    #ax.set_xlim(0, 10)
    #ax.set_ylim(20, 25)
    #ax.hold(True)


    # Cache background
    #background = fig.canvas.copy_from_bbox(ax.bbox)
    #points = ax.plot([], [], 'bo')[0]
    """
    fig, ax = plt.subplots()
    #½xdata, ydata = [], []
    ln, = plt.plot([], [], 'bo')
    savgol, = plt.plot([], [], 'r-')
    done, = plt.plot([], [], 'g-')
    
    def init():
        #xdata, ydata = reader.x, reader.y
        ax.set_xlim(0, 30)
        ax.set_ylim(19, 30)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Temperature')
        return ln, savgol, done

    def update(frame):
        #x, y = reader.x, reader.y
        if not reader.isAlive():
            #print('Return')
            global ifdone
            if ifdone is False:
                ifdone = True
                done.set_data(reader.x, savgol_filter(reader.y, reader.window, reader.order))
            print('Return\n')
            return ln, savgol, done
        try:
            #reader.print_data()
            xdata, ydata, y2 = reader.x[:], reader.y[:], reader.y_filter[:]
            #reader.print_data()
            #print(len(xdata))

            # Adjust axes
            update = False
            if max(xdata) > ax.get_xlim()[1]:
                ax.set_xlim(0, max(xdata) + 30)
                update = True
            ylim = ax.get_ylim()
            if max(ydata) > ylim[1] or min(ydata) < ylim[0]:
                ax.set_ylim(min(ydata), max(ydata))
                update = True
            if update:
                ax.figure.canvas.draw()

                
            if len(xdata) == len(ydata):
                ln.set_data(xdata, ydata)
            else:
                print('mismatch 1')
            if len(xdata) == len(y2):
                savgol.set_data(xdata, y2)
            else:
                print('mismatch 2')
            #print(xdata[-1], ydata[-1])
            #plt.plot(list(np.array(reader.x) - reader.t0), list(np.array(reader.y)), 'bo')
            return ln, savgol, done
            #print('Try:')
            #points.set_data(list(np.array(reader.x) - reader.t0), list(np.array(reader.y)))
            #fig.canvas.restore_region(background)
            #ax.draw_artist(points)
            #fig.canvas.blit(ax.bbox)
            #return (background, points, ax.bbox)
            #fig.canvas.draw()
            #ax.plot(, , 'o')
        except ValueError:
            print('Error')
            print(len(reader.x), len(reader.y))
            return ln, savgol

    
    #ani = FuncAnimation(fig, update, interval=1000, init_func=init, blit=True)

    print(3)
    #reader.start()
    #time.sleep(1)
    #plt.show()
    print(4)
    """
    while reader.isAlive():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            reader.quit = True
    #plt.show(False)
    #plt.draw()

    #for i in range(5):
    #    time.sleep(1)
    #    animate(0)
    #plt.title('All')
    #x = np.array(reader.x) - reader.t0
    #y = np.array(reader.y)
    #print(len(x), len(y))
    #plt.plot(x, y, 'o')
    #smooth = savgol_filter(y, 83, 1)
    #plt.plot(x, smooth, '-')
    #plt.show(False)
    #plt.draw()
    #print('After plt.show call')
    #dev.stop()

    #reader.quit = True

    #plt.plot(reader.x, reader.y, 'bo')
    #plt.plot(reader.x, reader.y_filter, 'r-', linewidth=2)
    #plt.plot(reader.x, savgol_filter(reader.y, 53, 1), 'k-')
    #plt.show()
    
    #send_cmd('slist 0 ' + str(0x1300))
    # Define sample rate = ?? Hz (refer to protocol:)
    # 8000/(srate * dec) = 8000/(4 * 10) = 200 Hz
    #send_cmd("dec 20")
    #send_cmd("dec 10")
    #send_cmd("srate 4")


