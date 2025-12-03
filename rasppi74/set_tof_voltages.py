""" Read the voltages from the analog voltage supply for the TOF """
from __future__ import print_function
import socket
import json
import PyExpLabSys.drivers.agilent_34972A as multiplexer
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

names = ['lens_a', 'lens_b', 'lens_c', 'lens_d', 'lens_e', '',  'focus', 'extraction']
defaults = [-135.1, -60, -36, -39.5, -41.9, 0, 12.8, -202]

def send_command(command):
    """ Send raw_wn command to local pushsocket """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)
    sock.sendto('raw_wn#{}'.format(command).encode(), ('127.0.0.1', 8500))
    try:
        received = sock.recv(1024).decode()
    except socket.timeout:
        print('Ion controller script not running properly!')
        raise
    print(received)

def set_voltages(channel='', voltage=0):
    """ Do the setting """
    if not channel in names:
        raise ValueError('Channel not in {}'.format(names))
    if not (voltage < 400 and voltage > -400):
        raise ValueError('Voltage must be in range ]-400, 400[')
    send_command("{}:float:{}".format(channel, voltage))

if __name__ == '__main__':
    pass
    #print(set_voltages())
