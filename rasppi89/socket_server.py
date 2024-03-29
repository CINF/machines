# pylint: disable=R0913,W0142,C0103
import threading
import time
import PyExpLabSys.drivers.mks_g_series as mks
from PyExpLabSys.common.sockets import DateDataPullSocket, DataPushSocket
from PyExpLabSys.common.sockets import LiveSocket


class FlowControl(threading.Thread):
    """ Keep updated values of the current flow """

    def __init__(self, mks_instance, mfcs, pullsocket, pushsocket, livesocket):
        threading.Thread.__init__(self)
        self.mfcs = mfcs
        self.mks = mks_instance
        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.livesocket = livesocket
        self.running = True

    def stop(self):
        self.running = False
        time.sleep(0.3)

    def run(self):
        while self.running:
            time.sleep(0.1)
            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                mfc = list(element.keys())[0]
                print(element[mfc])
                print('Queue: ' + str(qsize))
                value, addr = element[mfc], self.mfcs[mfc]
                if value >= 0:  # interpret it as a flow value
                    self.mks.set_flow(value, addr)
                elif value < 0:  # interpret as a purge time
                    self.mks.purge(value, addr)
                qsize = self.pushsocket.queue.qsize()

            for mfc in self.mfcs:
                flow = self.mks.read_flow(self.mfcs[mfc])
                print(mfc + ': ' + str(flow))
                self.pullsocket.set_point_now(mfc, flow)
                self.livesocket.set_point_now(mfc, flow)


port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTYIWNJ6-if00-port0'
devices = ['21984878', '21984877', '21984876', '21984879']

Datasocket = DateDataPullSocket(
    'sniffer_mks_mfc_control', devices, timeouts=[3.0] * len(devices), port=9000
)
Datasocket.start()

Pushsocket = DataPushSocket('sniffer_mks_push_control', action='enqueue')
Pushsocket.start()

Livesocket = LiveSocket('sniffer_mks_flows', devices)
Livesocket.start()

t0 = time.time()
i = 0
MFCs = {}
MKS = mks.MksGSeries(port=port)
for i in range(1, 8):
    time.sleep(0.25)
    serial = MKS.read_serial_number(i)
    print('Device {}: {}'.format(i, serial))
    if serial in devices:
        MFCs[serial] = i
        print('\tFull scale range: ', MKS.read_full_scale_range(i))
        print('\tRun hours: ', MKS.read_run_hours(i))
        print('\tTemperature: {}C'.format(MKS.read_internal_temperature(i)))
    if len(MFCs) == len(devices):
        break

print('Identified all MFCs in {:1.1f}s'.format(time.time() - t0))

FC = FlowControl(MKS, MFCs, Datasocket, Pushsocket, Livesocket)
FC.start()

while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        FC.stop()
        break
