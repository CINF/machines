#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VTUX Modbus TCP controller for Raspberry Pi (Holding Register bit-mapping)

- Controls VTUX via CPX-AP by writing/reading holding registers with bit masks

Mapping (from CPX-AP webservers Holding Register View - depends on hardware configuration):
  Outputs:
    HR 0:    bits 0..7  -> Module 3, coils 0..7
    HR 1:    bits 0..7  -> Module 4, coils 0..7
    HR 2:    bits 0..7  -> Module 5, coils 0..7
  Inputs:
    HR 5000: bits 0..7 -> Module 3, inputs 0..7
    HR 5001: bits 0..7 -> Module 4, inputs 0..7
    HR 5002: bits 0..7 -> Module 5, inputs 0..7

Standard-defaults match the mapping above.
"""

import argparse
import os
import sys
import time
from typing import Dict, List

# Tested with pymodbus version 3.12.1
try:
    from pymodbus.client import ModbusTcpClient
    from pymodbus.exceptions import ModbusException
except Exception:
    print("[ERROR] pymodbus is required. Install with: pip install pymodbus", file=sys.stderr)
    raise


class VTUXModbusHR:
    """Modbus TCP controller for VTUX via CPX-AP Holding Register bit fields."""

    def __init__(
        self,
        ip: str,
        port: int = 502,
        out_hr_base: int = 0,
        out_words: int = 3,      # HR 0..2
        in_hr_base: int = 5000,
        in_words: int = 3,       # HR 5000..5002
        timeout: float = 2.0,
    ) -> None:
        self.ip = ip
        self.port = port
        self.out_hr_base = out_hr_base
        self.out_words = out_words
        self.in_hr_base = in_hr_base
        self.in_words = in_words
        self.timeout = timeout

        self.client = ModbusTcpClient(host=self.ip, port=self.port, timeout=self.timeout)
        self.connect()
        self.outputs = self.read_valves()
        self.inputs = self.read_inputs()

    # Possibility for context manager
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # --- HR helpers ---
    def _read_hr_words(self, base: int, words: int) -> List[int]:
        if words <= 0:
            return []
        res = self._with_reconnect(self.client.read_holding_registers, address=base, count=words)
        if res is None or getattr(res, 'isError', lambda: True)():
            raise ModbusException(f"read_holding_registers failed at {base} len {words}: {res}")
        regs = list(getattr(res, 'registers', []) or [])
        if len(regs) != words:
            raise ModbusException(f"read_holding_registers returned {len(regs)} words, expected {words}")
        return regs

    def _write_single_hr(self, address: int, value: int) -> None:
        value &= 0xFFFF
        res = self._with_reconnect(self.client.write_register, address=address, value=value)
        if res is None or getattr(res, 'isError', lambda: True)():
            raise ModbusException(f"write_register failed at {address}: {res}")

    def _write_hr_words(self, base: int, values: List[int]) -> None:
        """Write multiple words; defaults to single write if FC16 is rejected by the unit."""
        if not values:
            return
        values = [int(v) & 0xFFFF for v in values]
        try:
            res = self._with_reconnect(self.client.write_registers, address=base, values=values)
            if res is None or getattr(res, 'isError', lambda: False)():
                for i, v in enumerate(values):
                    self._write_single_hr(base + i, v)
        except Exception:
            for i, v in enumerate(values):
                print('Debug: writing single: {} {}'.format(i, v))
                self._write_single_hr(base + i, v)

    def _reconnect(self):
        try:
            self.close()
        except Exception:
            pass
        time.sleep(0.2)
        self.connect()

    def _with_reconnect(self, func, *args, **kwargs):
        """Call Modbus function, reconnect once on failure, then re-raise."""
        try:
            return func(*args, **kwargs)
        except Exception:
            self._reconnect()
            return func(*args, **kwargs)

    # --- connection ---
    def connect(self) -> None:
        if not self.client.connect():
            raise ConnectionError(f"Failed to connect to Modbus TCP server at {self.ip}:{self.port}")

    def close(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass

    # --- outputs (valves) ---
    def set_valve(self, global_channel: int, state: bool) -> None:
        """
        global_channel: 1-based across 3 words of 8 bit each = 24 channels
          1..8  -> HR out_hr_base + 0, bit 0..7
          9..16 -> HR out_hr_base + 1, bit 0..7
          17..24-> HR out_hr_base + 2, bit 0..7
        """
        if global_channel < 1 or global_channel > self.out_words * 8:
            raise ValueError(f"channel must be 1..{self.out_words*8}")

        word_idx = (global_channel - 1) // 8
        bit_idx = (global_channel - 1) % 8
        words = self._read_hr_words(self.out_hr_base, self.out_words)

        current = words[word_idx]
        if state:
            new_word = current | (1 << bit_idx)
        else:
            new_word = current & ~(1 << bit_idx)

        if new_word != current:
            self._write_single_hr(self.out_hr_base + word_idx, new_word)

    def pulse_valve(self, global_channel: int, pulse_s: float) -> None:
        self.set_valve(global_channel, True)
        time.sleep(max(0.0, pulse_s))
        self.set_valve(global_channel, False)

    def set_multiple(self, channel_states: Dict[int, bool]) -> None:
        if not channel_states:
            return
        words = self._read_hr_words(self.out_hr_base, self.out_words)
        dirty_indices: List[int] = []
        for ch, st in channel_states.items():
            if ch < 1 or ch > self.out_words * 8:
                raise ValueError(f"channel {ch} must be 1..{self.out_words*8}")
            wi = (ch - 1) // 8
            bi = (ch - 1) % 8
            cur = words[wi]
            new_val = (cur | (1 << bi)) if st else (cur & ~(1 << bi))
            if new_val != cur:
                words[wi] = new_val
                dirty_indices.append(wi)
        for wi in sorted(set(dirty_indices)):
            self._write_single_hr(self.out_hr_base + wi, words[wi])

    def read_valves(self) -> List[bool]:
        words = self._read_hr_words(self.out_hr_base, self.out_words)
        #print(repr(words)) ###
        bits: List[bool] = []
        for w in words:
            for b in range(8):
                bits.append(bool((w >> b) & 0x1))
        return bits

    # --- inputs ---
    def read_inputs(self) -> List[bool]:
        words = self._read_hr_words(self.in_hr_base, self.in_words)
        #print(repr(words)) ###
        bits: List[bool] = []
        for w in words:
            for b in range(8):
                bits.append(bool((w >> b) & 0x1))
        return bits

    # --- raw ---
    def read_raw(self, base: int, count: int) -> List[int]:
        return self._read_hr_words(base, count)

    # --- blink ---
    def _set_group_state(self, channels: List[int], state: bool) -> None:
        if not channels:
            return
        words = self._read_hr_words(self.out_hr_base, self.out_words)
        dirty: Dict[int, int] = {}
        for ch in channels:
            if ch < 1 or ch > self.out_words * 8:
                raise ValueError(f"channel {ch} must be 1..{self.out_words*8}")
            wi = (ch - 1) // 8
            bi = (ch - 1) % 8
            cur = words[wi]
            new_val = (cur | (1 << bi)) if state else (cur & ~(1 << bi))
            if new_val != cur:
                words[wi] = new_val
                dirty[wi] = new_val
        for wi, val in dirty.items():
            self._write_single_hr(self.out_hr_base + wi, val)

    def blink(self, channels: List[int], on_s: float, off_s: float, cycles: int, sequential: bool = True) -> None:
        if not channels:
            return
        for ch in channels:
            if ch < 1 or ch > self.out_words * 8:
                raise ValueError(f"channel {ch} must be 1..{self.out_words*8}")
        cycles = max(1, int(cycles))
        on_s = max(0.0, float(on_s))
        off_s = max(0.0, float(off_s))

        if sequential:
            for _ in range(cycles):
                for ch in channels:
                    self.set_valve(ch, True)
                    time.sleep(on_s)
                    self.set_valve(ch, False)
                    time.sleep(off_s)
        else:
            for _ in range(cycles):
                self._set_group_state(channels, True)
                time.sleep(on_s)
                self._set_group_state(channels, False)
                time.sleep(off_s)


if __name__ == "__main__":
    try:
        ip = sys.argv[1]
    except IndexError:
        ip = '192.168.1.1'
    vtux = VTUXModbusHR(ip)
    print('Instance of VTUXModbusHR created as `vtux`')
