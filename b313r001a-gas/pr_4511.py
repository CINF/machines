import time
import logging
import minimalmodbus
import serial
import struct
from typing import Optional, Dict, Any

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.INFO)


class PR4511_4131:
    """
    Driver for PR electronics 4511 + PR 4131 universal trip amplifier (Modbus RTU).

    Process register map (Input Registers, FC=04) per PR 4131 MCM manual:
      1000: DISPLAY VALUE           (int; /10 for temperature inputs)
      1002: PERCENT PV              (int; 0..9999 => 0..100.00%)
      1003: MEASURE STATUS          (uint bitfield)
      1004: ERROR STATUS            (uint bitfield)
      1005: RELAY STATUS            (uint bitfield)
      1006: PRIMARY RAW VALUE       (float, 2 regs)
      1008: PRIMARY VALUE           (float, 2 regs)
      1010: RELATIVE PV             (float, 2 regs; 0.0..1.0)
      1014: MEASURE CONTROL         (uint R/W)
      1015: TIMEOUT COUNTER         (uint R/W)
      1016: INTERNAL TEMPERATURE    (int; /10 °C)
    """

    # Input register addresses (function code 4)
    REG = {
        "display_value": 1000,  # int (scaled); for temperature types: 1/10 °C
        "percent_pv": 1002,  # int (0..9999 -> 0..100.00 %)
        "measure_status": 1003,  # uint bitfield
        "error_status": 1004,  # uint bitfield
        "relay_status": 1005,  # uint bitfield
        "primary_raw": 1006,  # float (2 regs)
        "primary_value": 1008,  # float (2 regs)
        "relative_pv": 1010,  # float (2 regs) 0.0..1.0
        "measure_control": 1014,  # uint (R/W)
        "timeout_counter": 1015,  # uint (R/W)
        "internal_temp": 1016,  # int; /10 °C
    }

    def __init__(
        self,
        port: str,
        device_address: int,
        baudrate: int = 19200,
        parity=serial.PARITY_EVEN,
        stopbits: int = 1,
        timeout: float = 0.1,
    ):
        """
        :param port: '/dev/serial/by-id/<adapter-id>'
        :param device_address: 1..247 Modbus slave address of the 4511/4131
        """
        self.comm = minimalmodbus.Instrument(port, device_address)
        self.comm.serial.baudrate = baudrate
        self.comm.serial.parity = parity
        self.comm.serial.stopbits = stopbits
        self.comm.serial.timeout = timeout
        self.comm.mode = minimalmodbus.MODE_RTU
        self.comm.debug = False

        self.unit = ''
        try:
            self.version = self.comm.read_register(1)
            self.unit_number()
        except minimalmodbus.NoResponseError:
            print('Comms failed during __init__')
            self.version = -1

    def __str__(self):
        tagno = self.tag_number()
        value = self.read_display_value()
        return f"PR({tagno}): {value} {self.unit}"

    def __repr__(self):
        cls = type(self).__name__
        tagno = self.tag_number()
        value = self.read_display_value()
        return f"{cls}(address={self.comm.address}, tagno.=\"{tagno}\", value={value}, unit={self.unit})"

    # ---------------- low-level helpers ----------------

    def _read_input_regs(self, addr: int, count: int) -> Optional[list]:
        try:
            return self.comm.read_registers(addr, count, functioncode=4)
        except Exception as e:
            LOGGER.error(f"Read input regs failed at {addr}: {e}")
            return None

    def _read_uint16(self, addr: int) -> Optional[int]:
        regs = self._read_input_regs(addr, 1)
        return regs[0] if regs else None

    def _read_uint32(self, addr: int) -> Optional[int]:
        regs = self._read_input_regs(addr, 2)
        try:
            packed = struct.pack('>HH', regs[0] & 0xFFFF, regs[1] & 0xFFFF)
            return struct.unpack('>i', packed)[0]
        except Exception as e:
            LOGGER.error(f"Int decode error at {addr}: {e}")
            return None

    def _read_float32(self, addr: int) -> Optional[float]:
        regs = self._read_input_regs(addr, 2)
        if not regs or len(regs) != 2:
            return None
        try:
            packed = struct.pack('>HH', regs[0] & 0xFFFF, regs[1] & 0xFFFF)
            return struct.unpack('>f', packed)[0]
        except Exception as e:
            LOGGER.error(f"Float decode error at {addr}: {e}")
            return None

    # ---------------- public methods ----------------

    def unit_number(self, number=None):
        """Read or write the unit number"""
        if number is None:
            number = self.comm.read_register(14)
            if self.version in [1, 2, 3]:
                if number == 38:
                    self.unit = 'bar'
            return number
        # Otherwise write to device
        self.comm.write_registers(14, [number])

    def tag_number(self, tag=None):
        """Read or write the tag number. Only up to 6 characters will be written"""
        if tag is None:
            ret = self.comm.read_registers(55, 3)
            return (struct.pack("<3H", *ret).decode("ascii")).rstrip()
        tag = tag.upper().ljust(6)[:6]
        registers = list(struct.unpack("<3H", tag.encode("ascii")))
        self.comm.write_registers(55, registers)

    def identify_device(self):
        """Make the LCD screen flash for 10 seconds"""
        self.comm.write_registers(4001, [1])

    def read_relative_value(self):
        """The relative display value (fraction) of the full scale value"""
        return self._read_float32(self.REG["relative_pv"])

    def read_display_value(self) -> Optional[int]:
        """The displayed value in units"""
        value = self._read_uint32(self.REG["display_value"])
        if value:
            return value / 10

    def read_measure_status(self) -> Optional[int]:
        return self._read_uint16(self.REG["measure_status"])

    def read_error_status(self) -> Optional[int]:
        return self._read_uint16(self.REG["error_status"])

    def read_relay_status(self) -> Optional[int]:
        return self._read_uint16(self.REG["relay_status"])

    def read_timeout_counter(self) -> Optional[int]:
        return self._read_uint16(self.REG["timeout_counter"])

    # -------------- optional: bit decoding helpers --------------

    @staticmethod
    def decode_measure_status(bits: int) -> Dict[str, bool]:
        """
        Bits per PR 4131 manual:
          0: OUTPUT UNDERRANGE
          1: OUTPUT OVERRANGE
          2: OUTPUT LOW LIMITED
          3: OUTPUT HIGH LIMITED
          4: INPUT UNDERRANGE
          5: INPUT OVERRANGE
          6: SENSOR SHORTED
          7: SENSOR BROKEN
        """
        names = [
            "out_underrange",
            "out_overrange",
            "out_low_limited",
            "out_high_limited",
            "in_underrange",
            "in_overrange",
            "sensor_shorted",
            "sensor_broken",
        ]
        return {names[i]: bool(bits & (1 << i)) for i in range(len(names))}

    @staticmethod
    def decode_error_status(bits: int) -> Dict[str, bool]:
        """
        Error bits as listed (selection from manual; exact naming may vary by version):
          Bit 0+: supply / memory / ADC / CJC / output faults etc.
        We store the raw and the expanded 0..15 bits to avoid losing information.
        """
        return {f"err_bit_{i}": bool(bits & (1 << i)) for i in range(16)}

    @staticmethod
    def decode_relay_status(bits: int) -> Dict[str, bool]:
        """
        Per manual:
          0: RELAY 1 INVERTED
          1: RELAY 2 INVERTED
          2: RELAY 1 IS ON
          3: RELAY 2 IS ON
          4: RELAY 1 WILL GO ON AFTER DELAY
          5: RELAY 2 WILL GO ON AFTER DELAY
          6: RELAY 1 IS LATCHED (versions 2-3)
          7: RELAY 2 IS LATCHED (versions 2-3)
          8: RELAY 1 CAN NOT RELEASE
          9: RELAY 2 CAN NOT RELEASE
        """
        names = [
            "r1_inverted",
            "r2_inverted",
            "r1_on",
            "r2_on",
            "r1_pending",
            "r2_pending",
            "r1_latched",
            "r2_latched",
            "r1_cannot_release",
            "r2_cannot_release",
        ]
        return {names[i]: bool(bits & (1 << i)) for i in range(len(names))}


if __name__ == "__main__":
    port = "/dev/ttyUSB0"
    addr = 247  # Modbus slave address of this 4511/4131

    dev = PR4511_4131(port=port, device_address=addr)
    dev.identify_device()
    tagno = dev.tag_number()
    print(f"Connected to device with tag no.: {tagno}" if tagno is not None else "")

    display_value = dev.read_display_value()
    relative_value = dev.read_relative_value()
    measure_status = dev.read_measure_status()
    error_status = dev.read_error_status()
    relay_status = dev.read_relay_status()
    timeout_counter = dev.read_timeout_counter()

    # Console printout
    print(
        f"Display value   : {display_value:.3f}"
        if display_value is not None
        else "Display value   : ERROR"
    )
    print(
        f"Relative value  : {relative_value:.3f}"
        if relative_value is not None
        else "Relative value  : ERROR"
    )
    print(
        f"Measure status  : 0x{measure_status:04X}"
        if measure_status is not None
        else "Measure status  : ERROR"
    )
    print(
        f"Error status    : 0x{error_status:04X}"
        if error_status is not None
        else "Error status    : ERROR"
    )
    print(
        f"Relay status    : 0x{relay_status:04X}"
        if relay_status is not None
        else "Relay status    : ERROR"
    )
    print(
        f"Timeout counter : {timeout_counter}"
        if timeout_counter is not None
        else "Timeout counter : ERROR"
    )
