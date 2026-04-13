from sockets import GC_start_stop_socket
import time

gc = GC_start_stop_socket()

class Marker(object):
    def __init__(self):
        self._index = 0
        self._markers = ['-', '\\', '|', '/']

    def print(self, text):
        print(text + ' ' + self._markers[self._index], end='\r')
        self._index += 1
        if self._index > 3:
            self._index = 0

timer = time.time()
marker = Marker()
try:
    while True:
        marker.print(time.ctime())
        time.sleep(5)
        # Print a new line if an hour has passed
        if time.time() - timer > 3600:
            print('script still alive at ' + time.ctime())
            timer = time.time()
except KeyboardInterrupt:
    gc.stop()
