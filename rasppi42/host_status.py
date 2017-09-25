""" The program will check up status of a list of hosts """
import subprocess
import datetime
import telnetlib
import socket
import threading
import Queue
import time
import json
import sys
import os
import MySQLdb

def host_status(hostname, port):
    """ Report if a host i available on the network """
    host_is_up = True

    if port != '3389':
        try:
            subprocess.check_output(["ping", "-c1", "-W1", hostname])
        except subprocess.CalledProcessError:
            host_is_up = False
    if port == 3389: # RDP
        try:
            _ = telnetlib.Telnet(hostname, 3389)
        except socket.gaierror:
            host_is_up = False
        except socket.error:
            host_is_up = False
    return host_is_up

def uptime(hostname, port, username='pi', password='cinf123'):
    """ Fetch as much information as possible from a host """
    return_value = {}
    return_value['up'] = ''
    return_value['load'] = ''
    return_value['git'] = ''
    return_value['host_temperature'] = ''
    return_value['python_version'] = ''
    return_value['model'] = ''
    if port == 22: # SSH
        uptime_string = subprocess.check_output(["sshpass",
                                                 "-p",
                                                 password,
                                                 "ssh",
                                                 '-o LogLevel=quiet',
                                                 '-oUserKnownHostsFile=/dev/null',
                                                 '-oStrictHostKeyChecking=no',
                                                 username + "@" + hostname,
                                                 'cat /proc/uptime /proc/loadavg'])
        uptime_raw = uptime_string.split('\n')[0]
        uptime_value = str(int(float(uptime_raw.split()[0]) / (60*60*24)))
        load = uptime_string.split('\n')[1].split()[2]
        return_value['up'] = uptime_value
        return_value['load'] = load

    ports = []
    if not port in [22, 3389]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)

        try:
            sock.sendto('status', (hostname, port))            
            received = sock.recv(4096)
            status = json.loads(received)
            system_status = status['system_status']
            uptime_value = str(int(system_status['uptime']['uptime_sec']) / (60*60*24))
            load = str(system_status['load_average']['15m'])
            return_value['up'] = uptime_value
            return_value['load'] = load
        except:
            return_value['up'] = 'Down'
            return_value['load'] = 'Down'

        try:
            if system_status['purpose']['id'] is not None:
                return_value['location'] = system_status['purpose']['id']
                return_value['purpose'] = system_status['purpose']['purpose']
        except (KeyError, UnboundLocalError):
            pass
            
        try:
            model = system_status['rpi_model']
            host_temperature = system_status['rpi_temperature']
        except (KeyError, UnboundLocalError):
            model = ''
            host_temperature = ''

        try:
            python_version = system_status['python_version']
        except (KeyError, UnboundLocalError):
            python_version = ''
        return_value['model'] = model
        return_value['host_temperature'] = host_temperature
        return_value['python_version'] = python_version

        try:
            apt_up_time = system_status['last_apt_cache_change_unixtime']
            apt_up = datetime.datetime.fromtimestamp(apt_up_time).strftime('%Y-%m-%d')
        except UnboundLocalError:
            apt_up = ''
        return_value['apt_up'] = apt_up

        try:
            gittime = system_status['last_git_fetch_unixtime']
            git = datetime.datetime.fromtimestamp(gittime).strftime('%Y-%m-%d')
        except TypeError:
            git = 'None'
        except  UnboundLocalError:
            git = ''
        return_value['git'] = git

        # If host has been determined to be down, we attempt to load from cache
        if return_value['up'] == 'Down':
            pass
            #host_cache = pickle.load(open(CACHE_PATH + hostname + '.p', 'rb'))
            #return_value['git'] = host_cache['git']
            #return_value['model'] = host_cache['model']
            #return_value['python_version'] = host_cache['python_version']
        else: # Update cache
            pass
            #pickle.dump(return_value, open(CACHE_PATH + hostname + '.p', 'wb'))

    return return_value

class CheckHost(threading.Thread):
    """ Perfom the actual check """

    def __init__(self, hosts_queue, results_queue):
        threading.Thread.__init__(self)
        self.hosts = hosts_queue
        self.results = results_queue

    def run(self):
        while not self.hosts.empty():
            host = self.hosts.get_nowait()
            try:
                attr = json.loads(host[5])
            except TypeError: # Happens if attr is empty
                attr = {}
                attr['git'] = ''
                attr['model'] = ''
                attr['python_version'] = ''
            host_is_up = host_status(host[1], host[2])

            if host_is_up:
                if host[1].find('rasppi') > -1:
                    uptime_val = uptime(host[1], host[2])
                else:
                    uptime_val = uptime(host[1], host[2], username='cinf')
            else:
                uptime_val = {}
                uptime_val['up'] = ''
                uptime_val['load'] = ''
                uptime_val['git'] = attr['git']
                uptime_val['host_temperature'] = ''
                uptime_val['model'] = attr['model']
                uptime_val['python_version'] = attr['python_version']

            uptime_val['db_id'] = host[0]
            uptime_val['hostname'] = host[1]
            uptime_val['up_or_down'] = host_is_up
            uptime_val['port'] = host[2]
            if not 'location' in uptime_val:
                uptime_val['location'] = '<i>' + host[3] + '</i>'
                uptime_val['purpose'] = '<i>' + host[4] + '</i>'
            self.results.put(uptime_val)

            self.hosts.task_done()

def main():
    """ Main function """
    t = time.time()
    hosts = Queue.Queue()

    #TODO: The contact information should not be in this file!
    database = MySQLdb.connect(host='servcinf-sql', user='cinf_reader',
                               passwd='cinf_reader', db='cinfdata')
    cursor = database.cursor()
    query = 'select id, host, port, location, purpose, attr from host_checker;'
    cursor.execute(query)
    results = cursor.fetchall()
    for result in results:
        hosts.put(result)

    results = Queue.Queue()
    t = time.time()
    host_checkers = {}
    for i in range(0, 20):
        host_checkers[i] = CheckHost(hosts, results)
        host_checkers[i].start()
    hosts.join()

    sorted_results = {}
    i = 0
    while not results.empty():
        i = i + 1
        result = results.get()
        sorted_results[i] = result

    status_string = ""
    for host in sorted_results.values():
        if host['up_or_down']:
            query = ("update host_checker set attr = '" +
                     json.dumps(host) + "' where id = " + str(host['db_id']))
            print(query)
            cursor.execute(query)

if __name__ == "__main__":
    main()
