""" Temperature controller """
import time
import threading
import socket
#import curses

import PyExpLabSys.drivers.cpx400dp as CPX
import PyExpLabSys.aux.pid as PID


class TemperatureClass(threading.Thread):
    """ Read temperature off the local socekt server """
    def __init__(self):
        threading.Thread.__init__(self)
        self.temperature = None
        self.quit = False

    def read_temperature(self):
        """ Return the current temperature """
        return(self.temperature)

    def run(self):
        data = 'temperature#raw'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        while not self.quit:
            sock.sendto(data, ('localhost', 9000))
            received = sock.recv(1024)
            self.temperature = float(received[received.find(',') + 1:])
            time.sleep(0.5)


class PowerCalculatorClass(threading.Thread):
    """ Calculate the wanted amount of power """
    def __init__(self, temperature_reader):
        threading.Thread.__init__(self)
        self.tr = temperature_reader
        self.power = 0
        self.setpoint = -500
        self.pid = PID.PID()
        self.pid.UpdateSetpoint(setpoint)
        self.quit = False

    def read_power(self):
        """Return the calculated wanted power"""
        return(self.power)

    def update_setpoint(self, setpoint):
        self.setpoint = setpoint
        self.pid.UpdateSetpoint(setpoint)
        return(setpoint)

    def run(self):
        while not self.quit:
            self.power = self.pid.WantedPower(self.tr.read_temperature())
            self.pid.UpdateSetpoint(self.setpoint)
            time.sleep(0.25)


class HeaterClass(threading.Thread):
    """ Do the actual heating """
    def __init__(self, power_calculator):
        threading.Thread.__init__(self)
        self.pc = power_calculator
        self.heater = CPX.CPX400DPDriver(1,usbchannel=0)

    def run(self):
        print(self.heater.OutputStatus())
        print(self.heater.ReadActualCurrent())
        time.sleep(1)

T = TemperatureClass()
T.start()

P = PowerCalculatorClass(T)
P.start()

H = HeaterClass(P)
H.start

while True:
    time.sleep(1)

"""
# Calibrate resistance of the heaters
I_calib = {}
R_calib = {}
RTD = {}

for i in range(1,4):
    Heater[i].SetVoltage(3)
    Heater[i].OutputStatus(True)
    time.sleep(1)
    I_calib[i] = Heater[i].ReadActualCurrent()
    Heater[i].OutputStatus(False)
    R_calib[i] = 3/I_calib[i]
    RTD[i] = RTD_Calculator.RTD_Calculator(tc_temperature,R_calib[i])

time.sleep(1)

P = PowerCalculatorClass()
P.start()

TellTheWorld("Calibration value: {0:.5f} ohm at {1:.1f}C".format(T.rtd.Rrt,T.rtd.Trt),[2,1])
TellTheWorld("Calibration value, I1: {0:.3f} ohm at {1:.1f}C".format(RTD[1].Rrt,T.rtd.Trt),[2,2])
TellTheWorld("Calibration value, I2: {0:.3f} ohm at {1:.1f}C".format(RTD[2].Rrt,T.rtd.Trt),[2,3])
TellTheWorld("Calibration value, I3: {0:.3f} ohm at {1:.1f}C".format(RTD[3].Rrt,T.rtd.Trt),[2,4])

for i in range(1,4):
    Heater[i].SetVoltage(0)
    Heater[i].OutputStatus(True)


power = 0
I = {}
while not quit:
    try:
        time.sleep(0.25)
        setpoint = setpoint = ReadSetpoint()

        #RIGHT NOW WHENEVER POWER IS REPLACED WIDTH VOLTAGE!!!!!
        Heater[1].SetVoltage(P.power)
        Heater[2].SetVoltage(P.power)
        Heater[3].SetVoltage(P.power*0.8)
        for i in range(1,4):
            I[i] = Heater[i].ReadActualCurrent()

        U = P.power
        if I[1]<-99999998 or I[2]<-99999998 or I[3]<-99999998:
            
            for i in range(1,4):
                del Heater[i]

            Heater[1] = CPX.CPX400DPDriver(1,usbchannel=1)
            Heater[2] = CPX.CPX400DPDriver(2,usbchannel=0)
            Heater[3] = CPX.CPX400DPDriver(1,usbchannel=0)
            for i in range(1,4):
                I[i] = Heater[i].ReadActualCurrent()

        for i in range(1,4):
            if I[i]>0.01:
                TellTheWorld("R" + str(i) + ":  {0:.2f}           ".format(U/I[i]),[15*i-13,7])
                TellTheWorld("T" + str(i) + ": {0:.2f}     ".format(RTD[i].FindTemperature(U/I[i])),[15*i-13,8])
            else:
                TellTheWorld("R" + str(i) + ": -                  ",[15*i-13,7])
                TellTheWorld("T" + str(i) + ": -                      ",[15*i-13,8])


        TellTheWorld("Setpoint: " + str(setpoint) + "     ",[2,10])
        set_rtdval(T.temperature) # Check that the return value is actually true...
        TellTheWorld("Temperature: {0:.4f}".format(T.temperature),[2,11])      
        TellTheWorld("RTD resistance: {0:.5f}".format(T.rtd_value),[2,12])

        TellTheWorld("I1: {0:.3f}".format(I[1]),[2,14])
        TellTheWorld("I2: {0:.3f}".format(I[2]),[17,14])
        TellTheWorld("I3: {0:.3f}".format(I[3]),[32,14])

        TellTheWorld("Actual Voltage: {0:.4f}".format(U),[2,16])
        TellTheWorld("Wanted power: {0:.4f}".format(P.power),[2,17])
        TellTheWorld("Actual power: {0:.4f}".format(P.power*I[1]+ P.power*I[2] + 0.8*P.power*I[3]),[2,18])
        #time_since_sync = time.time() - Network.last_sync

        if output == 'curses':
            screen.refresh()
    except:
        quit = True

        if output == 'curses':
            curses.nocbreak()
            screen.keypad(0)
            curses.echo()
            curses.endwin()
        
        print "Program terminated by user"
        print sys.exc_info()[0]
        print sys.exc_info()[1]
        print sys.exc_info()[2]

for i in range(1,4):
    Heater[i].OutputStatus(False)
"""
