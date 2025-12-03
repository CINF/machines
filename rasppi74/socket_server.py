""" Read voltages from the Time-of-Flight and expose to network """
from __future__ import print_function
import socketserver
import threading
import time
import PyExpLabSys.drivers.agilent_34972A as multiplexer
from PyExpLabSys.common.sockets import DataPushSocket
import read_tof_voltages


class AnimatedMarker(object):
    """Animated marker to show socketserver is alive"""
    def __init__(self):
        self.counter = 0
        self.chars = ['-', '\\', '|', '/']

    def print(self):
        char = self.chars[self.counter]
        if self.counter == len(self.chars) - 1:
            self.counter = 0
        else:
            self.counter += 1
        print(char, end='\r')


class SlowProcess(threading.Thread):
    """ Perfom a slow operation without blocking the network """
    def __init__(self, port=8501):
        threading.Thread.__init__(self)
        self.bias_values = {}
        self.update = False
        self.running = True
        self.recent_update = -1
        self.marker = AnimatedMarker()
        self.pushsocket = DataPushSocket('tof-socket-server', action='enqueue', port=port, return_format='string')
        self.pushsocket.start()

    def update_bias_string(self):
        """ Call helper to update actual voltages """
        self.bias_values = read_tof_voltages.read_voltages()

    def run(self):
        print('SlowProcess started...')
        while self.running:
            self.marker.print()
            #if self.update: # Force an update of bias values
            #    print('Updating bias string:')
            #    self.update_bias_string()
            #    print(self.bias_values)
            #    time.sleep(0.1)
            #    self.recent_update = 20
            #    self.update = False
            #else:
            #    self.recent_update = self.recent_update - 1
            #    time.sleep(1)
            #if self.recent_update < 0: # If not updated recently, do not trust store values
            #    if self.bias_values:
            #        print('Resetting bias string!')
            #    self.bias_values = {}

            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                print(element)
                # do stuff with element
                qsize = self.pushsocket.queue.qsize()
            time.sleep(0.1)


class MyUDPHandler(socketserver.BaseRequestHandler):
    """ Handle request to read or update store bias values """
    def handle(self):
        global bias
        #global pec
        global agilent
        global slow_handler

        received_data = self.request[0].decode().strip()
        print(received_data)
        data = "test"
        socket = self.request[1]

        command = 'start_tof_measurement'
        if received_data[0:len(command)] == command:
            val = float(received_data[len(command)+1:].strip())
            voltage = val
            string = "SOURCE:VOLT " + str(voltage/500.0) + ", (@204)"
            agilent.scpi_comm(string)
            print(string)
            slow_handler.update = True
            data = 'ok'

        command = 'read_voltages'
        if received_data[0:len(command)] == command:
            print('read voltages')
            data_values = read_tof_voltages.read_voltages()
            print('data_values', data_values)
            data = ''
            for key in data_values.keys():
                data += key + ':' + str(data_values[key]) + ' '
            print(data)

        command = 'stop_tof_measurement'
        if received_data[0:len(command)] == command:
            voltage = 0
            string = "SOURCE:VOLT " + str(voltage/500.0) + ", (@204)"
            agilent.scpi_comm(string)
            data = 'ok'

        command = 'read_bias'
        if received_data[0:len(command)] == command:
            data = str(bias)

        command = 'set_bias'
        if received_data[0:len(command)] == command:
            val = float(received_data[len(command)+1:].strip())
            bias = val
            data = "ok"
            print(val)
            print('set_bias')

        command = 'aps' #Ask pause status
        if received_data[0:len(command)] == command:
            data = str(slow_handler.update)
            print(data)

        print(command, self.client_address)
        socket.sendto(data.encode(), self.client_address)


if __name__ == "__main__":
    host, port = '10.54.7.74', 9696 # rasppi74

    bias = -1
    #pec = False
    agilent = multiplexer.Agilent34972ADriver(hostname='tof-agilent-34972a')

    slow_handler = SlowProcess(port=8501)
    slow_handler.start()

    server = socketserver.UDPServer((host, port), MyUDPHandler)
    #print(server.client_address)
    try:
        server.serve_forever()
    except:
        slow_handler.running = False
        print('Test')
