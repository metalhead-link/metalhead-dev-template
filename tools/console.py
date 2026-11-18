#!/usr/bin/env python3
"""Run console commands on a metalhead connected over USB and print the answers.

    python3 tools/console.py "<command>" ["<command>" ...]

For example "units sandbox" (the units' plugins, their CPU use, which crashed), "unitls" (the
unit files on the card), "cfgget" (the config it runs, and why not if it refused it),
"paramset trem:depth 50", "crashtrace" (why it last reset), "reboot". macOS; configui must not
have the port open at the same time.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'sdk', 'tools'))

try:
    from metalhead_serial import command, open_port     # noqa: E402
except ImportError:
    sys.exit('no unit SDK in sdk/: git submodule update --init')


def main(commands):
    if not commands:
        sys.exit(__doc__)
    fd = open_port()
    for c in commands:
        out = command(fd, c, timeout=10)
        lines = out.replace('\r', '').split('\n')
        # the echoed command and the trailing prompt are noise
        if lines and lines[0].strip() == c:
            lines = lines[1:]
        while lines and lines[-1].strip() in ('', '>'):
            lines.pop()
        print('\n'.join(lines))
    os.close(fd)


if __name__ == '__main__':
    main(sys.argv[1:])
