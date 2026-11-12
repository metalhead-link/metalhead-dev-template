#!/usr/bin/env python3
"""Checks every setup (setups/<setup>/<player>.txt) the way the firmware's config parser would,
plus what only this repository knows: the players in band.json and our units' plugins and
parameters. Prints file:line: message for each problem; exits 1 if there was one.

    python3 tools/check.py [file ...]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BUILTIN = {"ClickTrack", "Looper", "MotionLight", "Network", "Bus"}
ESSENTIALS = {"Utility", "EQ", "Compressor", "Delay", "Filter", "YAFR"}
SECTIONS = {"[units]", "[buses]", "[audioroutes]", "[midiroutes]", "[midimap]", "[usbdrivers]", "[presets]"}
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,30}$")
DEVICE = re.compile(r"^\.[^\s:]+$")
MIDI_SPEC = re.compile(r"^(cc|noteon|noteoff)\d{1,3}$")


def our_plugins():
    """{plugin name: set of parameter names} for every plugin in units/."""
    plugins = {}
    for c in sorted((ROOT / "units").glob("*/*.c")) + sorted((ROOT / "units").glob("*/*.cc")):
        src = c.read_text(errors="replace")
        params = set(re.findall(r'\{\s*\w+\s*,[^{}"]*"([A-Za-z0-9_]+)"\s*,\s*"', src))
        for name in re.findall(r'\.name\s*=\s*"([^"]+)"', src):
            plugins[name] = params
    return plugins


class Checker:
    def __init__(self, players, plugins):
        self.players = players
        self.plugins = plugins
        self.problems = 0

    def error(self, path, line, message):
        self.problems += 1
        print(f"{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}:{line}: {message}")

    def check(self, path):
        if path.stem not in self.players:
            self.error(path, 0, f"{path.stem} isn't a player in band.json")
        units, buses, presets, recalled = {}, set(), set(), []
        on_strip = set()
        section = None
        seen = set()
        for n, raw in enumerate(path.read_text(errors="replace").splitlines(), 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("["):
                if line == "[connect]":
                    self.error(path, n, "a setup never has a [connect] section: that is the device's own")
                    section = None
                elif line in SECTIONS:
                    # Lines name units declared above them; the only other rule is that a bus
                    # exists before routes use it
                    if line == "[buses]" and "[audioroutes]" in seen:
                        self.error(path, n, "[buses] comes after [units] and before [audioroutes]")
                    seen.add(line)
                    section = line
                else:
                    self.error(path, n, f"unknown section {line}")
                    section = None
                continue
            if section is None:
                self.error(path, n, "a line outside a section")
                continue
            words = line.split()
            fail = lambda m: self.error(path, n, m)

            if section == "[units]":
                if len(words) != 2:
                    fail("expected <name> <plugin>")
                    continue
                name, plugin = words
                if not NAME.match(name):
                    fail(f"bad unit name {name}")
                elif name == "preset":
                    fail('"preset" is reserved for [midimap] preset:<name>')
                elif name in units:
                    fail(f"duplicate unit name {name}")
                    continue
                if plugin not in BUILTIN | ESSENTIALS | set(self.plugins):
                    fail(f"unknown plugin {plugin} (not built in, not Essentials, not in units/)")
                units[name] = plugin

            elif section == "[buses]":
                bus, strip = words[0], words[1:]
                if not NAME.match(bus) or bus == "preset":
                    fail(f"bad bus name {bus}")
                elif bus in units or bus in buses:
                    fail(f"duplicate bus or unit name {bus}")
                buses.add(bus)
                for u in strip:
                    if u not in units:
                        fail(f"unknown unit {u} on the strip (declare it in [units] first)")
                    elif u in on_strip:
                        fail(f"{u} is already on a strip")
                    on_strip.add(u)

            elif section == "[audioroutes]":
                if len(words) not in (2, 3):
                    fail("expected <source> <sink> [gain]")
                    continue
                for end in words[:2]:
                    who, _, channel = end.rpartition(":")
                    if not who or not channel.isdigit() or int(channel) < 1:
                        fail(f"bad endpoint {end} (unit:channel, bus:channel or .Device_Name:channel)")
                    elif not DEVICE.match(who) and who not in units and who not in buses:
                        fail(f"unknown unit or bus {who}")
                if len(words) == 3:
                    try:
                        gain = float(words[2])
                        if not 0 <= gain <= 16:
                            fail(f"gain {words[2]} out of range")
                    except ValueError:
                        fail(f"bad gain {words[2]}")

            elif section == "[midiroutes]":
                if len(words) != 2:
                    fail("expected <source> <sink>")
                    continue
                for end in words:
                    if not DEVICE.match(end) and end not in units:
                        fail(f"unknown unit {end} (or .Device_Name)")

            elif section == "[midimap]":
                if len(words) != 2:
                    fail("expected [.Device_Name:]<cc41|noteon60|noteoff60> <unit>:<parameter>")
                    continue
                spec = words[0].rsplit(":", 1)[-1] if words[0].startswith(".") else words[0]
                if not MIDI_SPEC.match(spec):
                    fail(f"unknown MIDI message {spec} (cc41, noteon60, noteoff60)")
                target = words[1]
                if target.startswith("preset:"):
                    recalled.append((n, target[7:]))
                else:
                    self.parameter(target, units, fail)

            elif section == "[usbdrivers]":
                if len(words) != 2 or not DEVICE.match(words[0]):
                    fail("expected .<device> <driver>")

            elif section == "[presets]":
                if len(words) != 3:
                    fail("expected <preset> <unit>:<parameter> <0..127>")
                    continue
                presets.add(words[0])
                self.parameter(words[1], units, fail)
                if not words[2].isdigit() or int(words[2]) > 127:
                    fail(f"preset value {words[2]} isn't 0..127 (as a MIDI controller sends)")

        for n, name in recalled:
            if name not in presets:
                self.error(path, n, f"preset {name} has no lines in [presets]")

    def parameter(self, spec, units, fail):
        unit, _, param = spec.partition(":")
        if not param:
            fail(f"expected <unit>:<parameter>, not {spec}")
        elif unit not in units:
            fail(f"unknown unit {unit}")
        elif units[unit] in self.plugins and self.plugins[units[unit]] and param not in self.plugins[units[unit]]:
            known = ", ".join(sorted(self.plugins[units[unit]]))
            fail(f"{units[unit]} has no parameter {param} ({known})")


def main(argv):
    band = json.loads((ROOT / "band.json").read_text())
    checker = Checker(set(band.get("players", {})), our_plugins())
    files = [Path(a).resolve() for a in argv] or sorted((ROOT / "setups").glob("*/*.txt"))
    for f in files:
        checker.check(f)
    print(f"{len(files)} setup file{'s' if len(files) != 1 else ''}, {checker.problems} problem{'s' if checker.problems != 1 else ''}")
    return 1 if checker.problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
