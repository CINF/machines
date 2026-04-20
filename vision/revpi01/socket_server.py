import time
from vtux_modbus import VTUXModbusHR
from PyExpLabSys.common.sockets import DateDataPullSocket, DataPushSocket

codenames = ['inputs', 'outputs', 'clients']

class Marker(object):
    def __init__(self):
        self._index = 0
        self._markers = ['-', '\\', '|', '/']

    def print(self, string):
        print(str(string) + '    ' + self._markers[self._index], end='\r')
        self._index += 1
        if self._index > 3:
            self._index = 0

marker = Marker()

pullsocket = DateDataPullSocket(
    'vision_gas_manifold_pull_socket',
    codenames=codenames,
    port=9000,
    timeouts=2,
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
    ip='10.196.162.30',
    port=502,
    out_hr_base=0,
    out_words=3,
    in_hr_base=5000,
    in_words=3,
    timeout=2,
)

for i in range(4):
    vtux.set_valve(i+1, False)

while True:
    time.sleep(0.2)
    qsize = pushsocket.queue.qsize()
    marker.print(qsize)
    while qsize > 0:
        command = pushsocket.queue.get()
        print(repr(command))
        qsize = pushsocket.queue.qsize()
        if 'set_valve' in command:
            conf = command['set_valve']
            vtux.set_valve(conf[0], bool(conf[1]))

    inputs = vtux.read_inputs()
    pullsocket.set_point_now('inputs', inputs)
    outputs = vtux.read_valves()
    pullsocket.set_point_now('outputs', outputs)
