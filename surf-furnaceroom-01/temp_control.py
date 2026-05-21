#! /usr/bin/python3
# pylint: disable=E1101, E0611
"""QtDesigner test"""
from __future__ import print_function
import sys
import time
import threading
import socket
#import pickle
import json
#from PyQt5 import Qt, QtCore
#from PyQt5.QtGui import QWidget
from PyQt5 import QtCore, QtWidgets
#import PyQt5.QtGui as pg
#import PyQt5.QtWidgets as pw
from temperature_controller_gui import Ui_temp_control, _translate
from PyExpLabSys.common.plotters import DataPlotter
#from PyExpLabSys.common.supported_versions import python2_only
from string_to_math import evaluate_string
import temperature_controller_config as config
#python2_only(__file__)


class TemperatureControllerComm(threading.Thread):
    """ Communicates with temperature controller over network """
    def __init__(self):
        threading.Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.5)
        self.running = True
        self.status = {}
        self.status['temperature'] = 0
        self.status['setpoint'] = 0
        self.status['dutycycle'] = 0
        self.status['connected'] = False
        self.status['temp_connected'] = False

    def read_param(self, param):
        """ Read a parameter from the controller """
        data = param + '#raw'
        error = 1
        # TODO: Investigate the reason for these network errors
        while (error < 50) and (error > 0):
            time.sleep(0.1)
            self.sock.sendto(data.encode(), (config.controller_hostname, config.controller_pull_port))
            received = self.sock.recv(1024).decode()
            ###print(received)
            try:
                value = float(received[received.find(',') + 1:])
                error = 0
                #print 'Error: ' + str(error)
            except ValueError:
                error = error + 1
                #print 'Error: ' + str(error)
                value = -1
        return value

    def run(self):
        while self.running is True:
            try:
                self.status['temperature'] = self.read_param('temperature')
                self.status['temp_connected'] = True
            except socket.error:
                self.status['temp_connected'] = False
            ###print(self.status['temp_connected'])
            try:
                self.status['dutycycle'] = self.read_param('dutycycle')
                ###print(self.status['dutycycle'])
                self.status['setpoint'] = self.read_param('setpoint')
                self.status['connected'] = True
            except socket.error:
                self.status['connected'] = False
            if not self.status['temp_connected']:
                self.status['connected'] = False
            time.sleep(0.2)


class SimplePlot(QtWidgets.QWidget):
    """Simple example with a Qwt plot in a Qt GUI"""
    def __init__(self, temp_control_comp):
        super(SimplePlot, self).__init__()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.5)

        self.tcc = temp_control_comp

        # Set up the user interface from Designer.
        self.gui = Ui_temp_control()
        self.gui.setupUi(self)

        # Init local variables
        self.scale = 1E-8
        self.active = False
        self.start = None
        self.ramp_start = 0 # Unused - moved to dict
        self.ramp_running = False
        self.ramp = {}
        self.ramp['time'] = {}
        self.ramp['temp'] = {}
        self.ramp['step'] = {}
        self.ramp['ramp_start'] = 0
        # Set up plot (using pretty much all the possible options)
        self.plots_l = ['temperature', 'setpoint']
        self.plots_r = ['dutycycle']
        self.plotter = DataPlotter(
            self.plots_l, right_plotlist=self.plots_r, parent=self,
            left_log=False, title='Temperature control',
            yaxis_left_label='Temperature', yaxis_right_label='Dutycycle',
            xaxis_label='Time since start [s]',
            legend='right', left_thickness=[2, 3], right_thickness=2,
            left_colors=['firebrick', 'darkolivegreen'],
            right_colors=['darksalmon'])
        self.gui.horizontalLayout.removeWidget(self.gui.place_holder_qwt)
        self.gui.place_holder_qwt.setParent(None)
        self.gui.horizontalLayout.addWidget(self.plotter.plot)

        # Connect signals
        self.gui.start_ramp_button.setCheckable(False) # Button was set to toggle
        self.gui.start_ramp_button.clicked.connect(self.on_start_ramp)
        self.gui.stop_ramp_button.clicked.connect(self.on_stop_ramp)
        self.gui.start_button.clicked.connect(self.on_start)
        self.gui.stop_button.clicked.connect(self.on_stop)
        self.gui.quit_button.clicked.connect(QtCore.QCoreApplication.instance().quit)
        self.gui.new_setpoint.returnPressed.connect(self.update_setpoint)
        time_tooltip = """Time (s).
        Note that you can enter simple math expressions using the operators: ()*/+-
        Afterwards, hover over the cell to display the evaluated result."""
        item = self.gui.temperature_ramp.horizontalHeaderItem(0)
        item.setToolTip(time_tooltip)
        temp_tooltip = """Temperature setpoint (Celcius)"""
        item = self.gui.temperature_ramp.horizontalHeaderItem(1)
        item.setToolTip(temp_tooltip)
        step_tooltip = """Step function enabled/disabled
        If step is enabled: the temperature setpoint is a stepfunction and the time
    indicates the duration of the setpoint.
        If step is disabled: the temperature is ramped up to temperature setpoint
    linearly over the time specified in the first column. To hold the temperature
    for a specified time period, enter this in the next row."""
        item = self.gui.temperature_ramp.horizontalHeaderItem(2)
        item.setToolTip(step_tooltip)
        self.gui.temperature_ramp.itemChanged.connect(self.edit_table)

        # Enable/disable buttons
        self.gui.stop_button.setEnabled(False)
        self.gui.start_ramp_button.setEnabled(False)
        self.gui.stop_ramp_button.setEnabled(False)

    def edit_table(self, item):
        """Interpreter for changing the ramp table parameters"""
        row, column = item.row(), item.column()
        # Wrap time column to allow simple math expressions
        if column == 0:
            item.setToolTip(evaluate_string(item.text(), verbose=False))

    def on_start(self):
        """Start button method"""
        print('<< start pressed >>')
        if not self.active:
            self.start = time.time()
            self.active = True
            # Reset plot
            for key in self.plotter.data.keys():
                self.plotter.data[key] = []
            QtCore.QTimer.singleShot(0, self.plot_iteration)
            self.gui.start_button.setEnabled(False)
            self.gui.start_ramp_button.setEnabled(True)
            self.gui.stop_button.setEnabled(True)
        else:
            state = self.gui.start_button.text()
            ack = self.push_command('raw_wn#ramp:str:pause')
            if ack:
                if state == 'Pause ramp':
                    self.gui.start_button.setText(_translate("temp_control", "Ramp paused", None))
                elif state == 'Ramp paused':
                    self.gui.start_button.setText(_translate("temp_control", "Pause ramp", None))
            print('...already running - toggling PAUSE function!')

    def verify_setpoint(self, setpoint):
        """Verify that setpoint is within allowed limits"""
        try:
            setpoint = float(setpoint)
        except ValueError:
            message = '...ValueError: {}\nOriginal setpoint used instead.'.format(repr(new_setpoint))
            setpoint = str(self.tcc.status['setpoint'])
            print(message)
            return setpoint
        if setpoint > config.MAX_TEMP:
            print('Temperature setpoint too high! Reduced to {}'.format(config.MAX_TEMP))
            return config.MAX_TEMP
        elif setpoint < 0:
            print('Subzero temperature setpoint changed to 0!')
        return setpoint

    def update_setpoint(self):
        """Update setpoint button method"""
        print('<< Updating setpoint >>')
        new_setpoint = self.gui.new_setpoint.text()
        new_setpoint = self.verify_setpoint(new_setpoint)
        self.gui.new_setpoint.setProperty("text", new_setpoint)
        data = 'raw_wn#setpoint:float:' + str(new_setpoint)
        self.sock.sendto(data.encode(), (config.controller_hostname, config.controller_push_port))
        received = self.sock.recv(1024)
        print(received)

    def push_command(self, command):
        """Send a command via the configured push socket. Return True if acknowledged"""
        if not isinstance(command, bytes):
            command = command.encode()
        self.sock.sendto(command, (config.controller_hostname, config.controller_push_port))
        received = self.sock.recv(1024).decode()
        if received.startswith('ACK'):
            print('Command {} succesfully received: {}'.format(command, received))
            return True
        print(received)
        return False

    def on_start_ramp(self):
        """Start temperature ramp"""
        print('<< Start ramp pressed >>')
        if not self.ramp_running:
            self.ramp_running = True
            self.ramp['init'] = True
        else:
            self.ramp['init'] = False
        for i in range(0, 11):
            self.ramp['time'][i] = float(evaluate_string(self.gui.temperature_ramp.item(i, 0).text(), verbose=False))
            self.ramp['temp'][i] = float(self.gui.temperature_ramp.item(i, 1).text())
            self.ramp['step'][i] = int(self.gui.temperature_ramp.item(i, 2).checkState()) == 2
        data = 'json_wn#' + json.dumps({'ramp': self.ramp})
        ack = self.push_command(data)
        if ack and self.ramp_running:
            # Enable/disable buttons
            self.gui.start_ramp_button.setText(_translate("temp_control", "Update ramp", None))
            self.gui.stop_ramp_button.setEnabled(True)
            self.gui.start_button.setEnabled(True)
            self.gui.start_button.setText(_translate("temp_control", "Pause ramp", None))

    def on_stop_ramp(self):
        """Stop temperature ramp"""
        print('<< Stop ramp pressed >>')
        data = 'raw_wn#ramp:str:stop'
        self.sock.sendto(data.encode(), (config.controller_hostname, config.controller_push_port))
        received = self.sock.recv(1024)
        print(received)
        if received.decode().startswith('ACK'):
            print('Ramp succesfully stopped')
            self.ramp_running = False
            #
            self.gui.start_button.setText(_translate("temp_control", "Start", None))
            self.gui.start_ramp_button.setText(_translate("temp_control", "Start ramp", None))
            self.gui.stop_ramp_button.setEnabled(False)
            self.gui.start_button.setEnabled(False)
            self.gui.stop_button.setEnabled(True)
        else:
            print('Ramp failed to stop. Try again or check communications.')

    def on_stop(self):
        """Stop button method"""
        print('<< Stop pressed >>')
        self.active = False
        # Enable start button
        self.gui.start_button.setText(_translate("temp_control", "Start plot", None))
        self.gui.start_button.setEnabled(True)
        self.gui.start_ramp_button.setEnabled(False)
        self.gui.stop_ramp_button.setEnabled(False)
        self.gui.stop_button.setEnabled(False)

    def plot_iteration(self):
        """method that emulates a single data gathering and plot update"""
        elapsed = time.time() - self.start
        if self.tcc.status['connected'] is True:
            self.gui.temperature.setProperty("text", str(self.tcc.status['temperature']) + ' C')
            self.gui.power.setProperty("text", '{:.4f}'.format(self.tcc.status['dutycycle']) + ' W')
            self.gui.setpoint.setProperty("text", str(self.tcc.status['setpoint']) + ' C')

        else:
            self.gui.current.setProperty("text", '-')
            self.gui.voltage.setProperty("text", '-')
            self.gui.temperature.setProperty("text", '-')
            self.gui.power.setProperty("text", '-')
            self.gui.resistance.setProperty("text", '-')
            self.gui.setpoint.setProperty("text", '-')
        try:
            if self.tcc.status['temp_connected'] is True:
                self.plotter.add_point('temperature',
                                       (elapsed, self.tcc.status['temperature']))
            if self.tcc.status['connected'] is True:
                self.plotter.add_point('setpoint', (elapsed, self.tcc.status['setpoint']))
                self.plotter.add_point('dutycycle', (elapsed, self.tcc.status['dutycycle']))
        except TypeError:
            pass

        if self.active:
            # Under normal curcumstances we would not add a delay
            QtCore.QTimer.singleShot(500, self.plot_iteration)


def main():
    """Main method"""
    tcc = TemperatureControllerComm()
    tcc.start()

    app = QtWidgets.QApplication(sys.argv)
    testapp = SimplePlot(tcc)
    testapp.show()
    app.exec_()
    print('Stop TCC...')
    tcc.running = False
    print('Script stopped!')

if __name__ == '__main__':

    main()
