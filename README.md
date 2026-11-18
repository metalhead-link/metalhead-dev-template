# My metalhead

What my metalhead runs, in one repository: the **setups** (the `metalhead.txt` it runs for a
rehearsal, a gig, a recording) and the **units** I write myself (audio and MIDI plugins in C, with
their faceplates). It is made for working with a coding agent such as Claude Code: `CLAUDE.md`
tells every session how this repository works, and the device can be built for, deployed to and
read from the command line.

This repository started from
[metalhead-dev-template](https://github.com/metalhead-link/metalhead-dev-template). A band uses
it the same way, with a player per bandmate in `project.json` (see *Several players* below).

| Path | What |
|---|---|
| `project.json` | the project and its players: who has which board |
| `setups/<setup>/<player>.txt` | a player's `metalhead.txt` in that setup; `README.md` says what the setup is for |
| `units/<unit>/` | a unit: its C source, `Makefile`, `README.md` and optionally a faceplate |
| `sdk/` | the [metalhead unit SDK](https://github.com/metalhead-link/metalhead-unit-sdk) (a submodule): the ABI, the build rules, the test runner |
| `tools/check.py` | checks every setup against the config language and the units here |
| `tools/deploy.py` | builds units and puts them on a metalhead connected over USB, then shows its console |
| `tools/console.py` | runs console commands on that metalhead |
| `CLAUDE.md` | how this repository works, for me and for every agent session on it |
| `.github/workflows/build.yml` | builds and tests every unit for both CPUs, checks the setups |

## Starting

Use this template on GitHub (*Use this template*), or clone it, then:

```sh
git clone --recurse-submodules <your repository>
python3 tools/check.py                 # the setups
make -C units test                     # every unit's plugins run on this computer, with sanitizers
make -C units                          # every unit, for both CPUs (needs the toolchains, below)
```

Units are built with two cross compilers:

- **Raspberry Pi 4 and 5** (`aarch64`): Arm's `arm-gnu-toolchain` for `aarch64-none-elf` (15.x),
  from developer.arm.com. Put its `bin/` on the `PATH`, or pass `CROSSPATH_AARCH64=`.
- **BeagleBone Black** (`arm32`): `arm-none-eabi-gcc` with newlib (Debian/Ubuntu: `apt install
  gcc-arm-none-eabi libnewlib-arm-none-eabi`; macOS: Arm's `arm-none-eabi` toolchain).

`units/toolchain.mk` finds both on the `PATH`. `make test` needs neither, and setups need nothing.

## Trying a unit on the device

With the metalhead on USB (its USB-C or USB device port to this computer; macOS for now):

```sh
python3 tools/deploy.py tremolo            # build for a Raspberry Pi, upload, show the console
python3 tools/deploy.py --bbb tremolo      # for a BeagleBone Black
python3 tools/deploy.py --reboot tremolo   # replacing a unit that is loaded takes a reboot
python3 tools/console.py "units sandbox"   # the units' plugins, their CPU use, which crashed
```

A unit is used by a setup like a built-in plugin (`[units]` `trem Tremolo`). Units run
unprivileged: one that faults is stopped and reported on the console as `Unit+offset`, and the
device keeps playing; `sdk/README.md` (*Units run unprivileged*) says how to read the report.

Over the internet, through metalhead.link: open the device from its room, paste a setup into
configui's Config tab, upload a unit from the release (below) in its Units tab. That needs a
device that allows the full remote console (`[connect] console=full`, or WiFi).

## On GitHub

The workflow runs on every push and pull request: it checks the setups, builds every unit for
both CPUs and runs their tests. On `main` it also publishes the unit files and a `units.json`
(each file's CPU and boards, size, sha256 and commit) as the release `units-latest`.

## Several players

A band keeps one repository for all its metalheads: a player per bandmate in `project.json`, a
`setups/<setup>/<player>.txt` per player, and each player working on it in their own agent
session, on branches, with pull requests where the band agrees on a change. `CLAUDE.md` has the
rules for that (*Working with others*).
