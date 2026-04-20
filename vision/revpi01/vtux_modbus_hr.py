#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VTUX Modbus TCP controller for Raspberry Pi (Holding Register bit-mapping)

- Controls VTUX via CPX-AP by writing/reading holding registers with bit masks
- Compatible with both older `pymodbus` (unit=) og newer `pymodbus` (slave=)
- CLI: set (with pulse), set-multiple, read-valves (bits), read-inputs (bits), blink (sequence/parallel), read-raw

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
import inspect
from typing import Dict, List

try:
    from pymodbus.client import ModbusTcpClient
    from pymodbus.exceptions import ModbusException
except Exception:
    print("[ERROR] pymodbus is required. Install with: pip install pymodbus", file=sys.stderr)
    raise


def _detect_unit_kw(client: ModbusTcpClient, fn_name: str = "read_holding_registers") -> Dict[str, int]:
    """Returns correct keyword for pymodbus API (unit or slave)."""
    try:
        fn = getattr(client, fn_name, None)
        print(client, fn_name, fn)
        if fn is None:
            return {}
        sig = inspect.signature(fn)
        print(sig)
        print(sig.parameters)
        if 'slave' in sig.parameters:
            return {'slave': None}
        if 'unit' in sig.parameters:
            return {'unit': None}
    except Exception:
        pass
    return {}


class VTUXModbusHR:
    """Modbus TCP controller for VTUX via CPX-AP Holding Register bit fields."""

    def __init__(
        self,
        ip: str,
        port: int = 502,
        unit_id: int = 1,
        out_hr_base: int = 0,
        out_words: int = 3,      # HR 0..2
        in_hr_base: int = 5000,
        in_words: int = 3,       # HR 5000..5002
        timeout: float = 2.0,
    ) -> None:
        self.ip = ip
        self.port = port
        self.unit_id = unit_id
        self.out_hr_base = out_hr_base
        self.out_words = out_words
        self.in_hr_base = in_hr_base
        self.in_words = in_words
        self.timeout = timeout

        self.client = ModbusTcpClient(host=self.ip, port=self.port, timeout=self.timeout)

        # Choose correct keyword ('unit' eller 'slave') for pymodbus call
        self.kw = _detect_unit_kw(self.client, "read_holding_registers")
        print(repr(self.kw))
        if "slave" in self.kw:
            self.kw["slave"] = self.unit_id
        elif "unit" in self.kw:
            self.kw["unit"] = self.unit_id
        else:
            print('No "KW" detected')

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

    # Possibility for context manager
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # --- connection ---
    def connect(self) -> None:
        if not self.client.connect():
            raise ConnectionError(f"Failed to connect to Modbus TCP server at {self.ip}:{self.port}")

    def close(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass

    # --- HR helpers ---
    def _read_hr_words(self, base: int, words: int) -> List[int]:
        if words <= 0:
            return []
        res = self._with_reconnect(self.client.read_holding_registers, address=base, count=words, **self.kw)
        if res is None or getattr(res, 'isError', lambda: True)():
            raise ModbusException(f"read_holding_registers failed at {base} len {words}: {res}")
        regs = list(getattr(res, 'registers', []) or [])
        if len(regs) != words:
            raise ModbusException(f"read_holding_registers returned {len(regs)} words, expected {words}")
        return regs

    def _write_single_hr(self, address: int, value: int) -> None:
        value &= 0xFFFF
        res = self._with_reconnect(self.client.write_register, address=address, value=value, **self.kw)
        if res is None or getattr(res, 'isError', lambda: True)():
            raise ModbusException(f"write_register failed at {address}: {res}")

    def _write_hr_words(self, base: int, values: List[int]) -> None:
        """Write multiple words; defaults to single write if FC16 is rejected by the unit."""
        if not values:
            return
        values = [int(v) & 0xFFFF for v in values]
        try:
            res = self._with_reconnect(self.client.write_registers, address=base, values=values, **self.kw)
            if res is None or getattr(res, 'isError', lambda: False)():
                for i, v in enumerate(values):
                    self._write_single_hr(base + i, v)
        except Exception:
            for i, v in enumerate(values):
                self._write_single_hr(base + i, v)

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
        bits: List[bool] = []
        for w in words:
            for b in range(8):
                bits.append(bool((w >> b) & 0x1))
        return bits

    # --- inputs ---
    def read_inputs(self) -> List[bool]:
        words = self._read_hr_words(self.in_hr_base, self.in_words)
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


# --- CLI ---

def _parse_channel_list(text: str) -> List[int]:
    result: List[int] = []
    if not text:
        return result
    chunks = [c.strip() for c in text.split(',') if c.strip()]
    for c in chunks:
        if '-' in c:
            a, b = c.split('-')
            a = int(a)
            b = int(b)
            rng = range(min(a, b), max(a, b) + 1)
            result.extend(rng)
        else:
            result.append(int(c))
    return sorted(set(result))


def _parse_args(argv: List[str]) -> argparse.Namespace:
    # Common parser
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--ip", "--host", "-H", default=os.getenv("VTUX_IP", "10.196.162.30"), help="Modbus TCP server IP (accepts host or host:port)")
    common.add_argument("--port", type=int, default=int(os.getenv("VTUX_PORT", "502")), help="Modbus TCP port")
    common.add_argument("--unit", type=int, default=int(os.getenv("VTUX_UNIT", "1")), help="Modbus Unit/Slave ID")
    common.add_argument("--out-hr-base", type=int, default=int(os.getenv("VTUX_OUT_BASE", "0")), help="Outputs HR base address")
    common.add_argument("--out-words", type=int, default=int(os.getenv("VTUX_OUT_WORDS", "3")), help="Outputs words count")
    common.add_argument("--in-hr-base", type=int, default=int(os.getenv("VTUX_IN_BASE", "5000")), help="Inputs HR base address")
    common.add_argument("--in-words", type=int, default=int(os.getenv("VTUX_IN_WORDS", "3")), help="Inputs words count")
    common.add_argument("--timeout", type=float, default=float(os.getenv("VTUX_TIMEOUT", "2.0")), help="Modbus TCP timeout seconds")
    common.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    common.add_argument("--hold", type=float, default=0.0, help="Hold connection and refresh last output state for N seconds (default 0: off)")
    common.add_argument("--refresh", type=float, default=0.5, help="Refresh period in seconds while holding (default 0.5)")

    parser = argparse.ArgumentParser(description="Control Festo VTUX via Modbus TCP (Holding Registers)", parents=[common])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_set = sub.add_parser("set", help="Set a single valve ON/OFF", parents=[common])
    p_set.add_argument("channel", type=int, help="Global valve channel (1-based)")
    p_set.add_argument("state", choices=["on", "off"], help="Desired state")
    p_set.add_argument("--pulse", type=float, default=0.0, help="Optional pulse seconds (ON then OFF)")

    p_multi = sub.add_parser("set-multiple", help="Set multiple valves in one request", parents=[common])
    p_multi.add_argument("pairs", nargs="+", help="Pairs like 1=on 9=off ...")

    sub.add_parser("read-inputs", help="Read digital inputs (bit view)", parents=[common])
    sub.add_parser("read-valves", help="Read output valve states (bit view)", parents=[common])

    p_blink = sub.add_parser("blink", help="Blink valves (sequential or parallel)", parents=[common])
    p_blink.add_argument("--channels", required=True, help="List like 1,3-5,8 (1-based)")
    p_blink.add_argument("--on", type=float, default=0.3, help="ON time in seconds")
    p_blink.add_argument("--off", type=float, default=0.3, help="OFF time in seconds")
    p_blink.add_argument("--cycles", type=int, default=5, help="Number of cycles")
    mode = p_blink.add_mutually_exclusive_group()
    mode.add_argument("--sequential", action="store_true", help="Blink sequentially (default)")
    mode.add_argument("--parallel", action="store_true", help="Blink all channels simultaneously")

    p_raw = sub.add_parser("read-raw", help="Read raw holding registers", parents=[common])
    p_raw.add_argument("--base", type=int, required=True, help="HR base address")
    p_raw.add_argument("--count", type=int, default=1, help="Number of words to read (default 1)")
    p_raw.add_argument("--as-bits", action="store_true", help="Print each word as 8 LSB bits")

    args = parser.parse_args(argv)

    # host:port support
    if isinstance(args.ip, str) and ':' in args.ip:
        host, _, maybe_port = args.ip.partition(':')
        args.ip = host.strip()
        try:
            if maybe_port:
                args.port = int(maybe_port)
        except ValueError:
            raise ValueError(f"Invalid --ip format '{args.ip}:{maybe_port}'. Use host or host:port.")

    return args


def main(argv: List[str]) -> int:
    args = _parse_args(argv)
    if args.verbose:
        print(f"[INFO] Connecting to {args.ip}:{args.port} unit={args.unit} timeout={args.timeout}s")
    ctrl = VTUXModbusHR(
        ip=args.ip,
        port=args.port,
        unit_id=args.unit,
        out_hr_base=args.out_hr_base,
        out_words=args.out_words,
        in_hr_base=args.in_hr_base,
        in_words=args.in_words,
        timeout=args.timeout,
    )
    try:
        ctrl.connect()
        if args.cmd == "set":
            if getattr(args, 'pulse', 0.0) and args.pulse > 0:
                ctrl.pulse_valve(args.channel, args.pulse)
                print(f"Pulsed valve {args.channel} for {args.pulse:.3f}s")
            else:
                desired = (args.state == "on")
                ctrl.set_valve(args.channel, desired)
                print(f"Set valve {args.channel} -> {args.state}")
                if args.hold and args.hold > 0:
                    t0 = time.time()
                    print(f"[HOLD] Holding valve {args.channel} -> {'on' if desired else 'off'} for {args.hold:.2f}s (refresh {args.refresh:.3f}s)")
                    next_tick = 0
                    while True:
                        elapsed = time.time() - t0
                        if elapsed >= args.hold:
                            break
                        ctrl.set_valve(args.channel, desired)
                        if args.verbose and elapsed >= next_tick:
                            remaining = max(0.0, args.hold - elapsed)
                            print(f"[HOLD] valve {args.channel} {'on' if desired else 'off'} | remaining {remaining:.2f}s")
                            next_tick = elapsed + 0.5
                        time.sleep(max(0.01, args.refresh))
                    print(f"[HOLD] Done holding valve {args.channel}")
        elif args.cmd == "set-multiple":
            states: Dict[int, bool] = {}
            for pair in args.pairs:
                try:
                    ch_str, st_str = pair.split("=")
                    ch = int(ch_str)
                    st = True if st_str.lower() in ("on", "1", "true", "t") else False
                    states[ch] = st
                except Exception:
                    raise ValueError(f"Invalid pair '{pair}', expected N=on|off")
            ctrl.set_multiple(states)
            print("Set states:")
            for ch, st in sorted(states.items()):
                print(f"  valve {ch}: {'on' if st else 'off'}")
            if args.hold and args.hold > 0:
                t0 = time.time()
                print(f"[HOLD] Holding {len(states)} valves for {args.hold:.2f}s (refresh {args.refresh:.3f}s)")
                next_tick = 0
                while True:
                    elapsed = time.time() - t0
                    if elapsed >= args.hold:
                        break
                    ctrl.set_multiple(states)
                    if args.verbose and elapsed >= next_tick:
                        remaining = max(0.0, args.hold - elapsed)
                        summary = ', '.join([f"{ch}={'on' if st else 'off'}" for ch, st in sorted(states.items())])
                        print(f"[HOLD] {summary} | remaining {remaining:.2f}s")
                        next_tick = elapsed + 0.5
                    time.sleep(max(0.01, args.refresh))
                print("[HOLD] Done holding multiple valves")
        elif args.cmd == "read-inputs":
            vals = ctrl.read_inputs()
            for i, v in enumerate(vals, start=1):
                print(f"IN{i}: {'1' if v else '0'}")
        elif args.cmd == "read-valves":
            vals = ctrl.read_valves()
            for i, v in enumerate(vals, start=1):
                print(f"OUT{i}: {'1' if v else '0'}")
        elif args.cmd == "blink":
            channels = _parse_channel_list(args.channels)
            sequential = True
            if args.parallel:
                sequential = False
            elif args.sequential:
                sequential = True
            ctrl.blink(channels, on_s=args.on, off_s=args.off, cycles=args.cycles, sequential=sequential)
            print(f"Blink done on channels {channels} (mode={'sequential' if sequential else 'parallel'})")
        elif args.cmd == "read-raw":
            regs = ctrl.read_raw(args.base, args.count)
            for i, w in enumerate(regs):
                if args.as_bits:
                    bits = ''.join(str((w >> b) & 1) for b in range(7, -1, -1))
                    print(f"HR[{args.base + i:>5}] = 0x{w:04X} ({w:5d})  bits7..0={bits}")
                else:
                    print(f"HR[{args.base + i:>5}] = 0x{w:04X} ({w:5d})")
        else:
            raise RuntimeError("Unknown command (no subcommand matched)")
        return 0
    except (ConnectionError, ModbusException, ValueError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    finally:
        ctrl.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
