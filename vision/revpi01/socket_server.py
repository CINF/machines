import time
import threading
from vtux_modbus import VTUXModbusHR
from PyExpLabSys.common.sockets import DateDataPullSocket, DataPushSocket, CLIENTS

codenames = ['inputs', 'outputs', 'clients']

class Marker(object):
    """Spinning marker to indicate update loop"""
    def __init__(self):
        self._index = 0
        self._markers = ['-', '\\', '|', '/']

    def print(self, string):
        print(str(string) + '    ' + self._markers[self._index], end='\r')
        self._index += 1
        if self._index > 3:
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
        self.t0 = time.time()
        while True:
            time.sleep(0.15)
            if not self.event and time.time() - self.t0 > self.timeout:
                self.event = True

    def reset(self):
        self.t0 = time.time()
        self.event = False

    def activate(self):
        self.event = True

marker = Marker()
timer = Timer(timeout=2)
timer.start()

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

for i in range(4): ###
    vtux.set_valve(i+1, False) ###

clients = {}
timer.reset()
inputs = vtux.read_inputs()
while True:
    time.sleep(0.15)
    qsize = pushsocket.queue.qsize()
    marker.print(qsize)
    while qsize > 0:
        command = pushsocket.queue.get()
        print(time.ctime(), repr(command))
        qsize = pushsocket.queue.qsize()
        if 'set_valve' in command:
            ip = command.get('ip')
            if not ip or ip not in clients:
                print(f'Invalid set_valve command: {command}')
                continue
            # Set new valve status
            conf = command['set_valve']
            vtux.set_valve(conf[0], bool(conf[1]))

            # Read values
            time.sleep(0.1)
            timer.activate()
            print(time.time())
            print('timeout activated')

        elif 'enlist' in command:
            clients[command['ip']] = {
                'name': command['hostname'],
                'time': time.time(),
            }
            print(f'Client {command["hostname"]} connected')

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

    for ip in list(CLIENTS.keys()):
        if ip in clients:
            clients[ip]['time'] = CLIENTS[ip]
