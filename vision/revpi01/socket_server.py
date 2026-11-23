import time
import threading
from vtux_modbus import VTUXModbusHR
from PyExpLabSys.common.sockets import DateDataPullSocket, DataPushSocket, CLIENTS
import revpimodio2 as rpio2 # Input/outputs library

codenames = ['inputs', 'outputs', 'clients',
             'pressure_gas1', 'pressure_gas2', 'pressure_gas3', 'pressure_uhv',
             'voltage_gas1', 'voltage_gas2', 'voltage_gas3', 'voltage_uhv']

class Marker(object):
    """Crawling worm to indicate update loop"""
    def __init__(self):
        self._index = 0
        self.march = 35
        self._march_counter = 0
        self._path = ' '*self.march
        self._direction = 1
        self._markers = ['___', '__/', '_/\\', '/\\_', '\\__']

    def print(self, string):
        print(str(string) + '    ' + self._path[:self._march_counter] + self._markers[self._index], end=' '*self.march + '\r')
        self._march_counter += self._direction
        if self._march_counter == self.march:
            self._direction = -1
            self._markers.reverse()
        elif self._march_counter == 0:
            self._direction = 1
            self._markers.reverse()
        self._index += 1
        if self._index > len(self._markers) - 1:
            self._index = 0

class Timer(threading.Thread):
    """Thread to indicate timeout events"""
    def __init__(self, timeout=1):
        super().__init__()
        self.timeout = timeout
        self.event = False
        self.daemon = True
        self.t0 = None

    def run(self):
        self.counter = self.timeout
        while True:
            time.sleep(0.06)
            self.counter -= 0.06
            if not self.event and self.counter < 0:
                self.event = True

    def reset(self):
        self.counter = self.timeout
        self.event = False

    def activate(self):
        self.event = True


marker = Marker()
timer = Timer(timeout=2)
timer.start()

rpi = rpio2.RevPiModIO(autorefresh=True)

pullsocket = DateDataPullSocket(
    'vision_gas_manifold_pull_socket',
    codenames=codenames,
    port=9000,
    timeouts=5,
)
pullsocket.start()

pushsocket = DataPushSocket(
    'vision_gas_manifold_push_socket',
    port=8500,
    action='enqueue',
    return_format='raw',
)
pushsocket.start()

vtux = VTUXModbusHR(
    #ip='10.196.162.30',
    ip='192.168.1.100',
    port=502,
    out_hr_base=0,
    out_words=3,
    in_hr_base=5000,
    in_words=3,
    timeout=2,
)
# TODO: default to closing all ports?

def sens4_pressure(voltage):
    """Convert sens4 voltage to pressure"""
    if voltage < 0.1:
        pressure = 'Undef'
    elif voltage < 0.5:
        pressure = 'Underrange'
    elif voltage > 9.5:
        pressure = 'Overrange'
    elif voltage > 10:
        pressure = 'Error'
    else:
        pressure = 10**(voltage - 6.5)
    return pressure

def pfeiffer_pressure(voltage):
    """Convert sens4 voltage to pressure"""
    if voltage < 0.1:
        pressure = 'Undef'
    elif voltage < 0.5:
        pressure = 'CError'
    elif voltage < 1.82:
        pressure = 'Underrange'
    elif voltage > 8.6:
        pressure = 'Overrange'
    elif voltage > 9.5:
        pressure = 'PError'
    else:
        pressure = 10**(1.667*voltage - 11.33)
    return pressure


pressure_uhv = None
pressure_gas1 = None
pressure_gas2 = None
pressure_gas3 = None
clients = {}
timer.reset()
inputs = vtux.read_inputs()
pressure_counter = 1
while True:
    time.sleep(0.1)
    qsize = pushsocket.queue.qsize()
    marker.print(qsize)
    while qsize > 0:
        command = pushsocket.queue.get()
        print(time.ctime(), repr(command))
        qsize = pushsocket.queue.qsize()
        if 'enlist' in command:
            clients[command['ip']] = {
                'name': command['hostname'],
                'time': time.time(),
            }
            print(f'Client {command["hostname"]} connected')
            continue

        ip = command.get('ip')
        if not ip or ip not in clients:
            print(f'Invalid command: {command} from {ip}')
            continue
        if 'set_valve' in command:
            # Set new valve status
            conf = command['set_valve']
            vtux.set_valve(conf[0], bool(conf[1]))
            # Read values
            timer.counter = 0.25

    # Pressures currently update with 5Hz
    if pressure_counter > 0:
        voltage_uhv = rpi.io.pressure_uhv()/1000
        #print(voltage_uhv)
        pressure_uhv = pfeiffer_pressure(voltage_uhv)
        pullsocket.set_point_now('pressure_uhv', pressure_uhv)
        pullsocket.set_point_now('voltage_uhv', voltage_uhv)
        voltage_gas1 = rpi.io.pressure_gas1()/1000
        pressure_gas1 = sens4_pressure(voltage_gas1)
        pullsocket.set_point_now('pressure_gas1', pressure_gas1)
        pullsocket.set_point_now('voltage_gas1', voltage_gas1)
        voltage_gas2 = rpi.io.pressure_gas2()/1000
        pressure_gas2 = sens4_pressure(voltage_gas2)
        pullsocket.set_point_now('pressure_gas2', pressure_gas2)
        pullsocket.set_point_now('voltage_gas2', voltage_gas2)
        voltage_gas3 = rpi.io.pressure_gas3()/1000
        pressure_gas3 = sens4_pressure(voltage_gas3)
        pullsocket.set_point_now('pressure_gas3', pressure_gas3)
        pullsocket.set_point_now('voltage_gas3', voltage_gas3)
    pressure_counter *= -1

    if timer.event:
        old_inputs = inputs.copy()
        inputs = vtux.read_inputs()
        for i, val in enumerate(inputs):
            if not inputs[i] and old_inputs[i] or not old_inputs[i] and inputs[i]:
                print(time.time())
                print(f'Valve {i+1} toggled')
        pullsocket.set_point_now('inputs', inputs)
        outputs = vtux.read_valves()
        pullsocket.set_point_now('outputs', outputs)

        # GUI clients
        now = time.time()
        for ip in list(clients.keys()):
            if now - clients[ip]['time'] > 5:
                host = clients[ip]['name']
                print(f'Client {host} disconnected')
                del clients[ip]
        pullsocket.set_point_now('clients', clients)

        # Reset event timer
        timer.reset()

    for ip in CLIENTS:
        if ip in clients:
            clients[ip]['time'] = CLIENTS[ip]
