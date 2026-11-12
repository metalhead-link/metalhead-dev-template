# Our band's metalheads

Everything our metalheads run, in one repository: the **setups** (each player's `metalhead.txt`
for a rehearsal, a gig, a recording) and the **units** we write ourselves (plugins in C, with
their faceplates). Each of us works on it with Claude Code, in their own session, on branches;
pull requests are how we agree on a change.

This repository started from metalhead-connect's `band-template/`.

| Path | What |
|---|---|
| `band.json` | the band and its players: who has which board |
| `setups/<setup>/<player>.txt` | one player's `metalhead.txt` in that setup; `README.md` says what the setup is for |
| `units/<unit>/` | a unit: its C source, `Makefile`, `README.md` and optionally a faceplate |
| `tools/check.py` | checks every setup against the config language and our units |
| `CLAUDE.md` | how we work, for us and for every Claude session on this repository |
| `.github/workflows/build.yml` | builds and tests every unit for both boards, checks the setups |

## Starting

```sh
git clone --recurse-submodules <this repository>
python3 tools/check.py                 # the setups
make -C units                          # every unit, for both boards (needs the toolchains, below)
make -C units test                     # every unit's plugins run on this computer
```

Units need the metalhead unit SDK in `sdk/` (`git submodule add
git@github.com:metalhead-link/metalhead-unit-sdk.git sdk`, or `make -C units SDK=/path/to/sdk`)
and two cross compilers:

- **Raspberry Pi 5:** Arm's `arm-gnu-toolchain` for `aarch64-none-elf` (15.x), from
  developer.arm.com. Put its `bin/` on the `PATH`, or pass `CROSSPATH_AARCH64=`.
- **BeagleBone Black:** `arm-none-eabi-gcc` with newlib (Debian/Ubuntu: `apt install
  gcc-arm-none-eabi libnewlib-arm-none-eabi`; macOS: Arm's `arm-none-eabi` toolchain).

`units/toolchain.mk` finds both on the `PATH`. You don't need them to work on setups.

## On GitHub

The workflow runs on every push and pull request: it checks the setups, builds every unit for
both boards and runs their tests. On `main` it also publishes the unit files and a
`units.json` (each file's board, size, sha256 and commit) as the release `units-latest`.

If the SDK repository is private, add a repository secret `SDK_TOKEN`: a fine-grained token that
can read `metalhead-link/metalhead-unit-sdk`.

## Trying things on a metalhead

For now, through configui: open the device from the room on metalhead.link, paste a setup into
its Config tab, upload a unit from the release in its Units tab. Writing the config and uploading
units need a device that allows the full remote console (`[connect] console=full`, or WiFi).
