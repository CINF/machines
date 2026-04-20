#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VTUX test sequence: open one valve at a time for a given duration, with refresh.
"""
import argparse
import sys
import time
from vtux_modbus_hr import VTUXModbusHR, _parse_channel_list


def parse_args(argv):
    p = argparse.ArgumentParser(description="VTUX one-by-one valve open test")
    p.add_argument("--ip", "--host", "-H", default="192.168.1.1", help="Modbus TCP server IP (host or host:port)")
    p.add_argument("--port", type=int, default=502, help="Modbus TCP port")
    p.add_argument("--unit", type=int, default=1, help="Modbus Unit/Slave ID")
    p.add_argument("--out-hr-base", type=int, default=0, help="Outputs HR base address")
    p.add_argument("--out-words", type=int, default=3, help="Outputs words count")
    p.add_argument("--on", type=float, default=1.0, help="Open duration per valve (seconds)")
    p.add_argument("--gap", type=float, default=0.2, help="Gap between valves (seconds)")
    p.add_argument("--refresh", type=float, default=0.1, help="Refresh period while holding (seconds)")
    p.add_argument("--channels", default="", help="List like 1,3-5,8 (1-based)")
    p.add_argument("--start", type=int, default=1, help="Start channel if --channels not set")
    p.add_argument("--end", type=int, default=24, help="End channel if --channels not set")
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = p.parse_args(argv)

    if isinstance(args.ip, str) and ':' in args.ip:
        host, _, maybe_port = args.ip.partition(':')
        args.ip = host.strip()
        if maybe_port:
            try:
                args.port = int(maybe_port)
            except ValueError:
                raise ValueError(f"Invalid --ip format: {host}:{maybe_port}")
    return args


def main(argv):
    args = parse_args(argv)
    if args.channels:
        channels = _parse_channel_list(args.channels)
    else:
        a, b = sorted((args.start, args.end))
        channels = list(range(a, b + 1))

    ctrl = VTUXModbusHR(ip=args.ip, port=args.port, unit_id=args.unit,
                        out_hr_base=args.out_hr_base, out_words=args.out_words, timeout=2.0)
    try:
        ctrl.connect()
        for ch in channels:
            if args.verbose:
                print(f"[SEQ] Opening valve {ch} for {args.on:.2f}s")
            t0 = time.time()
            while True:
                elapsed = time.time() - t0
                if elapsed >= args.on:
                    break
                ctrl.set_valve(ch, True)
                time.sleep(max(0.1, args.refresh))
            print(ctrl.read_inputs())
            ctrl.set_valve(ch, False)
            if args.verbose:
                print(f"[SEQ] Closed valve {ch}; gap {args.gap:.2f}s")
            time.sleep(max(0.0, args.gap))
        print("[SEQ] Done:", channels)
        return 0
    except KeyboardInterrupt:
        print("[SEQ] Aborted by user")
        return 130
    finally:
        ctrl.close()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
