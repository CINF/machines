"""Valve control for microreactor"""

import time
#import PyExpLabSys.common.valve_control as valve_control
import valve_control_gpiozero as valve_control
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket

class Marker(object):
    def __init__(self):
        self._index = 0
        self._markers = ['-', '\\', '|', '/']

    def print(self, text=0, spaces=3):
        print(f'{text}{" "*spaces}{self._markers[self._index]}{" "*spaces}', end='\r')
        self._index += 1
        if self._index > 3:
            self._index = 0

def main():
    """Main function"""
    valve_names = [0] * 20
    for i in range(0, 20):
        valve_names[i] = str(i + 1)

    pullsocket = DateDataPullSocket(
        'minireactor2 Valvecontrol', valve_names, timeouts=[2] * 20
    )
    pullsocket.start()

    pushsocket = DataPushSocket('minireactor2 valve control', action='enqueue')
    pushsocket.start()

    valve_controller = valve_control.ValveControl(valve_names, pullsocket, pushsocket)
    valve_controller.start()

    marker = Marker()

    while True:
        time.sleep(1)
        marker.print(text=valve_controller.qsize)

    valve_controller.running = False


if __name__ == '__main__':
    main()
