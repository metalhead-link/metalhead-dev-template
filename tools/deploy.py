#!/usr/bin/env python3
"""Build units and put them on a metalhead connected over USB, then show what the device says.

    python3 tools/deploy.py [--bbb] [--reboot] [--watch SECONDS] [unit ...]

Units are directories in units/ (default: all of them). Each is built for the board (make aarch64:
Raspberry Pi 4 and 5; --bbb: make arm32, the BeagleBone Black), uploaded over the device's USB
serial port (the console's unitput, as configui's Units tab does), and the device's console is
shown for a few seconds after (--watch), so a unit that fails to load, logs, or crashes says so
here. A unit already loaded on the device is replaced at the next boot: --reboot reboots it then,
and watches the boot.

macOS: the port is found by the device's USB product name (sdk/tools/metalhead_serial.py).
configui (or anything else) must not have the port open at the same time.
"""
import argparse
import os
import re
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
UNITS = os.path.join(ROOT, 'units')
SDK_TOOLS = os.path.join(ROOT, 'sdk', 'tools')
sys.path.insert(0, SDK_TOOLS)

try:
    from metalhead_serial import open_port     # noqa: E402
    from upload_units import put_unit          # noqa: E402
except ImportError:
    sys.exit('no unit SDK in sdk/: git submodule update --init')

MEANING = {
    'loaded': 'loaded',
    'unchanged': 'the same as the one loaded',
    'reboot': 'saved; replaces the loaded one at the next boot',
}


def unit_file(unit):
    """(NAME, BUNDLE) from a unit's Makefile"""
    text = open(os.path.join(UNITS, unit, 'Makefile')).read()
    name = re.search(r'^NAME\s*:=\s*(\S+)', text, re.M)
    bundle = re.search(r'^BUNDLE\s*:=\s*(\S+)', text, re.M)
    return name.group(1), bundle.group(1)


def watch(fd, seconds):
    """Print what the console says for a while (logs, load errors, crash reports)"""
    end = time.time() + seconds
    while time.time() < end:
        try:
            data = os.read(fd, 65536)
        except OSError:
            return False        # the device went away (a reboot)
        if data:
            sys.stdout.write(data.decode(errors='replace').replace('\r', ''))
            sys.stdout.flush()
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('units', nargs='*', help='directories in units/ (default: all)')
    parser.add_argument('--bbb', action='store_true', help='build for the BeagleBone Black (default: a Raspberry Pi)')
    parser.add_argument('--reboot', action='store_true', help='reboot when a replaced unit needs it')
    parser.add_argument('--watch', type=float, default=5, help='seconds of console output to show after (default 5)')
    args = parser.parse_args()

    units = args.units or sorted(d for d in os.listdir(UNITS) if os.path.isfile(os.path.join(UNITS, d, 'Makefile')))
    machine = 'arm32' if args.bbb else 'aarch64'
    files = []
    for unit in units:
        if not os.path.isfile(os.path.join(UNITS, unit, 'Makefile')):
            sys.exit(f'{unit}: no units/{unit}/Makefile')
        if subprocess.run(['make', '-s', '-C', os.path.join(UNITS, unit), machine]).returncode:
            sys.exit(f'{unit}: the build failed')
        name, bundle = unit_file(unit)
        files.append((bundle, os.path.join(UNITS, unit, 'build', machine, f'{name}.unt')))

    fd = open_port()
    failed, stale = False, []
    for bundle, path in files:
        print(f'{bundle}: {os.path.getsize(path)} bytes ... ', end='', flush=True)
        result = put_unit(fd, path)
        m = re.match(r'@unitput ok \S+ (\S+)', result)
        if m:
            print(MEANING.get(m.group(1), m.group(1)))
            if m.group(1) == 'reboot':
                stale.append(bundle)
        else:
            print(result.replace('@unitput ', ''))
            failed = True

    if stale and args.reboot:
        print('rebooting; the boot:')
        os.write(fd, b'reboot\r')
        watch(fd, 2)
        os.close(fd)
        time.sleep(3)
        fd = open_port()        # waits for the device to come back
        watch(fd, max(args.watch, 10))
    else:
        if stale:
            print(f'replaced at the next boot: {", ".join(stale)} (--reboot, or tools/console.py reboot)')
        watch(fd, args.watch)
    os.close(fd)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
