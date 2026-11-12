# CLAUDE.md

This repository is a band's: the setups and units its metalheads run. Several players work on it
at once, each with their own Claude Code session. Read `README.md` and `band.json` first.

## Working together

- **Branch, then pull request.** Never push to `main`. Name the branch after the player and the
  change (`alice/gig-setup`, `bob/tremolo-sync`). Pull before you start; another session may
  have changed what you are about to touch.
- **A player's file is theirs.** `setups/<setup>/<player>.txt` is what that player's device
  runs. Change another player's file only when that player asked, and say so in the PR.
  Shared changes (a new setup for everyone, a rename) go in one PR that every affected player
  reviews.
- **Say what it sounds like.** A PR describes the musical change (what each player hears, what
  moved where), not only the lines.
- **Run the checks before every commit:** `python3 tools/check.py`, and for units
  `make -C units test` (and `make -C units` when the toolchains are there). CI runs both.

## Setups: the config language

Each `setups/<setup>/<player>.txt` is a whole `metalhead.txt` (the firmware reads it from the SD
card at boot). Each line can only name units declared above it, so `[units]` comes first and
`[buses]` before `[audioroutes]`. The sections:

- `[units]`: `<name> <Plugin>`, a plugin instance. Built-in plugins: `ClickTrack`, `Looper`,
  `MotionLight`, `Network`, `Bus`. Others come from unit files on the card: Essentials
  (`Utility`, `EQ`, `Compressor`, `Delay`, `Filter`, `YAFR`, free for everyone) and ours in `units/`.
- `[buses]`: `<bus> [unit ...]`, a named stereo bus with an effect strip of `[units]` in series;
  `level` is its fader.
- `[audioroutes]`: `<source> <sink> [gain]`. Endpoints are `unit:channel`, `bus:channel` or
  `.Device_Name:channel` (a USB device by product name, `.device` is the computer).
- `[midiroutes]`: `<source> <sink>` (a unit or `.Device_Name`).
- `[midimap]`: `[.Device:]cc41|noteon60|noteoff60 <unit>:<parameter>` or `preset:<name>`.
- `[usbdrivers]`: `.<device> <Driver>`.
- `[presets]`: `<preset> <unit>:<parameter> <0..127>`; `startup` is sent at boot.

**Never put a `[connect]` section in a setup.** It holds the device's own server key and console
settings; metalhead.link keeps the device's own when a setup is applied, and `check.py` refuses
it. Device names in routes must match what the player's interface reports (its product name with
spaces as `_`); ask the player, or look at their device's current config.

## Units

A unit is native code that runs **in the device's audio interrupt** on bandmates' instruments.
Write it as if it were going on stage tonight:

- C99 (or C++14 without exceptions/RTTI), against `sdk/include/unit_abi.h` only. No libc: no
  `malloc`, `printf`, files or threads. `libm` with `LIBM := 1`. Static instance pools
  (`MAX_INSTANCES`), never allocation.
- `process()` is bounded and never blocks: no loops that depend on input data, no waiting.
  It must fit the **BeagleBone Black** (1 GHz Cortex-A8) as well as the Pi 5; if it can't,
  put it in `PLUGINS_aarch64` only and say so in the unit's README.
- Ramp every gain change (a few ms) so moving a control never clicks; check for NaN/denormals
  in feedback paths.
- Parameters have stable ids; never renumber them (presets and `[midimap]` lines name them).
- Every unit has `make test` (the SDK's `tools/unittest.c`, run with sanitizers). Add a WAV
  render when the sound matters (`TEST_ARGS="-w out/"`).
- A faceplate is optional: one self-contained HTML file, see `sdk/doc/faceplates.md`. It runs
  sandboxed and only talks to its own unit's parameters.

New unit: copy `units/tremolo/`, rename `NAME`, `BUNDLE`, the plugin entry function and the
plugin's `.name`. A plugin name is global on a device: don't reuse one from Essentials or
another unit. `BUNDLE` becomes `/units/<BUNDLE>.unt` on the card.

Never commit build output (`units/*/build/`), keys or tokens.
