# -*- coding: utf-8 -*-
"""
Driver for CS Instruments VA 521 via Modbus RTU

Reads Flow [m³/h], Velocity [m/s], Temperature [°C], and Total Consumption [m³]
https://www.cs-instruments.com

@author: asmos With assistance from ChatGPT
"""

import time
import logging
import minimalmodbus
import serial
import struct

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler())

class VA521(object):
    """Driver for the CS VA 521 inline flow sensor"""

    def __init__(self, port: str, device_address: int):
        self.comm = minimalmodbus.Instrument("/dev/serial/by-id/" + port, device_address)
        self.comm.serial.baudrate = 19200
        self.comm.serial.parity = serial.PARITY_EVEN
        self.comm.serial.stopbits = 1
        self.comm.serial.timeout = 1.5
        self.comm.mode = minimalmodbus.MODE_RTU
        self.comm.debug = False

        # Latest measurements
        self.flow = None
        self.velocity = None
        self.temperature = None
        self.total = None

    def _read_float32(self, reg_high, reg_low:
        """
        Read a 32-bit float from two registers.
        The VA521 uses 2 registers for a float.
        """
        try:
            regs = self.comm.read_registers(reg_low, 2, functioncode=3)
            high_word, low_word = regs[0], regs[1]
            packed = struct.pack('>HH', high_word, low_word)
            value = struct.unpack('>f', packed)[0]
            return value
        except Exception as e:
            LOGGER.error(f"Error reading float32 at {reg_low}-{reg_high}: {e}")
            return None

    def _read_uint32(self, reg_high, reg_low):
        """
        Read a 32-bit unsigned integer from two registers.
        Used for total consumption.
        """
        try:
            regs = self.comm.read_registers(reg_low, 2, functioncode=3)
            high_word, low_word = regs[0], regs[1]
            value = (high_word << 16) + low_word
            return value
        except Exception as e:
            LOGGER.error(f"Error reading uint32 at {reg_low}-{reg_high}: {e}")
            return None

    def read_flow(self):
        """Read the actual flow in m³/h"""
        self.flow = self._read_float32(1101, 1100)
        return self.flow

    def read_velocity(self):
        """Read the velocity in m/s"""
        self.velocity = self._read_float32(1347, 1346)
        return self.velocity

    def read_temperature(self):
        """Read the temperature in °C"""
        self.temperature = self._read_float32(1419, 1418)
        return self.temperature

    def read_total(self):
        """Read the total consumption in m³"""
        self.total = self._read_uint32(1269, 1268)
        return self.total


if __name__ == "__main__":
    port = '/dev/ttyUSB1'
    fm = VA521(port=port, device_address=1)
    
    flow = fm.read_flow()
    velocity = fm.read_velocity()
    temperature = fm.read_temperature()
    total = fm.read_total()
    
    print(f"Flow         : {flow:.3f} m³/h" if flow is not None else "Flow         : ERROR")
    print(f"Velocity     : {velocity:.3f} m/s" if velocity is not None else "Velocity     : ERROR")
    print(f"Temperature  : {temperature:.3f} °C" if temperature is not None else "Temperature  : ERROR")
    print(f"Total        : {total} m³" if total is not None else "Total        : ERROR")
    print("-" * 40)
    time.sleep(1)

