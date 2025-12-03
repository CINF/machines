import sys

from host_status import uptime

hostname = sys.argv[1]
port = int(sys.argv[2])

print(hostname)
s = '.fys.clients.local'
a = uptime(hostname, port, '', '')

print(a)
