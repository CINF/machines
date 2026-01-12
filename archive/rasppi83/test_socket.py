from PyExpLabSys.common.sockets import DataPushSocket
import time

if __name__ == '__main__':
    psocket = DataPushSocket('omicron_test_socket', action='store_last')
    psocket.start()

    while True:
        time.sleep(1)
        print(psocket.last)
