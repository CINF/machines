"""
This module implements the necessary interface to control
a valve box using standard gpio commands
"""
from __future__ import print_function
import time
import threading
#import wiringpi as wp
import gpiozero as gp
from PyExpLabSys.common.value_logger import LoggingCriteriumChecker

wiringpi_to_bcm = {
    0: 17,
    1: 18,
    2: 27,
    3: 22,
    4: 23,
    5: 24,
    6: 25,
    7: 4,
    8: 2,
    9: 3,
    10: 8,
    11: 7,
    12: 10,
    13: 9,
    14: 11,
    15: 14,
    16: 15,
    21: 5,
    22: 6,
    23: 13,
    24: 19,
    25: 26,
    26: 12,
    27: 16,
    28: 20,
    29: 21,
    30: 0,
    31: 1,
}

# For Rev. 2 using the P5 header for wiringpi pins 17-20, but having the header moved
# to pins 33-40 on a Pi4
translate = {
    0: 17,
    1: 18,
    2: 27,
    3: 22,
    4: 23,
    5: 24,
    6: 25,
    7: 4,
    8: 2,
    9: 3,
    10: 8,
    11: 7,
    12: 10,
    13: 9,
    14: 11,
    15: 14,
    16: 15,
    # From old P5 header
    17: 16,
    18: 19,
    19: 20,
    20: 26,
}

class ValveControl(threading.Thread):
    """ Keeps status of all valves """

    def __init__(self, valves, pullsocket, pushsocket, db_saver=None, codenames=None):
        """Initialize local properties

        Args:
            valves ():
            pullsocket ():
            pushsocket ():
            db_saver (:class:`.ContinuousDataSaver`): (Optional) If db_saver and
                codenames is given, valves states will be logged as continuous values
            codenames (list): (Optional) Iterable of codenames for the valve
                state logging, in order
        """
        threading.Thread.__init__(self)
        #wp.wiringPiSetup()
        time.sleep(1)
        self.outputs = {}
        for index in range(0, 21):  # Set GPIO pins to output
            #wp.pinMode(index, 1)
            #wp.digitalWrite(index, 0)
            self.outputs[index] = gp.LED(translate[index])
            self.outputs[index].off()
        # Now that all output are low, we can open main safety output
        #wp.digitalWrite(20, 1)
        self.outputs[20].on()

        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.running = True
        self.qsize = -1
        self.valves = valves

        self.db_saver = db_saver
        self.codenames = codenames
        if codenames is not None:
            print(codenames)
            self.logging_criterium_checker = LoggingCriteriumChecker(
                codenames,
                types=['lin'] * len(codenames),
                criteria=[0.1] * len(codenames),
                time_outs=[600] * len(codenames),
            )

    def run(self):
        while self.running:
            time.sleep(0.1)
            qsize = self.pushsocket.queue.qsize()
            self.qsize = qsize
            while qsize > 0:
                element = self.pushsocket.queue.get()
                valve = list(element.keys())[0]
                zero_numbered_valve_number = int(valve) - 1

                # If activated send valve state to database
                if self.db_saver and self.codenames:
                    try:
                        value_codename = self.codenames[zero_numbered_valve_number]
                    except IndexError:
                        pass
                    else:
                        # Check syntax for below
                        value = float(element[valve])
                        if self.logging_criterium_checker.check(value_codename, value):
                            self.db_saver.save_point_now(value_codename, value)

                #wp.digitalWrite(zero_numbered_valve_number, element[valve])
                if bool(element[valve]) is True:
                    self.outputs[zero_numbered_valve_number].on()
                else:
                    self.outputs[zero_numbered_valve_number].off()
                qsize = self.pushsocket.queue.qsize()

            for j in range(0, 20):
                #current_value = wp.digitalRead(j)
                current_value = self.outputs[j].is_lit
                self.pullsocket.set_point_now(self.valves[j], current_value)
                if self.db_saver and self.codenames:
                    try:
                        codename = self.codenames[j]
                    except IndexError:
                        pass
                    else:
                        value = float(current_value)
                        if self.logging_criterium_checker.check(codename, value):
                            self.db_saver.save_point_now(codename, value)
