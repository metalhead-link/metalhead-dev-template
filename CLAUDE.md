# CLAUDE.md

This repository holds what one or more metalheads run: setups (their `metalhead.txt`) and units
(plugins in C). Read `README.md` and `project.json` first: `project.json` says who the players
are and which board each has (`rpi5`, `rpi4`: a Raspberry Pi, `aarch64` units; `bbb`: a
BeagleBone Black, `arm32` units).

## Commands

```sh
python3 tools/check.py                     # every setup; run before every commit
make -C units test                         # every unit on this computer (sanitizers); before every commit
make -C units                              # both CPUs (needs the cross toolchains, README.md)
make -C units/<unit> stack                 # a unit's largest stack frames (it has 32 KB)
python3 tools/deploy.py [--bbb] [--reboot] <unit>   # build, upload over USB, show the console
python3 tools/console.py "<command>" ...   # e.g. "units sandbox", "unitls", "cfgget", "crashtrace"
```

## The loop for a unit

1. Write or change it in `units/<unit>/`; `make -C units/<unit> test` until it passes.
   `TEST_ARGS="-w out/"` renders each plugin to WAV files (notes into `midiIn`, a plucked
   sawtooth into its inputs) when the sound matters; listen, or check them with a script.
2. If a metalhead is connected over USB (`tools/console.py unitls` answers), deploy it:
   `tools/deploy.py --reboot <unit>` (`--bbb` for a BeagleBone, by the player's board in
   `project.json`). Read what the console says after: the unit's own `log()` lines, a load error,
   or a crash report.
3. To hear it, the device's config has to use it: `[units] <name> <Plugin>` and routes. A setup
   in `setups/` is what goes on the device; change the device's running config only when the
   player asked (`cfgget` shows it).
4. Check its cost: `tools/console.py "units sandbox"` gives each plugin's `process()` calls and
   cycles per call. A unit must fit the BeagleBone Black (1 GHz Cortex-A8), whose budget per
   block is far smaller than a Pi 5's; if it can't, it goes in `PLUGINS_aarch64` only and its
   README says so.

No device connected: do step 1, reason about step 4, and say in the commit or PR what was and
wasn't tried on hardware.

## Units

A unit is native code that runs **in the device's audio interrupt**, unprivileged (the SDK's
`README.md`, *Units run unprivileged*, and `sdk/include/unit_abi.h` are the contract). Write it as
if it were going on stage tonight:

- C99 (or C++14 without exceptions/RTTI) against `sdk/include/unit_abi.h` only. No libc: what
  the firmware offers is in `UnitHostApi` (`log`, `allocate`, reading files in `unit_entry()` or
  `createInstance()` only). `libm` with `LIBM := 1`.
- Memory: static instance pools (`MAX_INSTANCES`) or `allocate()` at creation; never in
  `process()`. **32 KB of stack**: big buffers are static or allocated, not local
  (`make stack`).
- `process()` is bounded and never blocks: no loops that depend on input data, no waiting.
- Pointers handed to the firmware point into the unit's own memory. The plugin structure, its
  strings and the channel and parameter counts are read once at load: keep them constant.
- Floating-point control (flush-to-zero, rounding) is reset after every call: set it at the start
  of `process()` if you need it. Check for NaN and denormals in feedback paths.
- Ramp every gain change (a few ms) so moving a control never clicks.
- Parameters have stable ids; never renumber them (presets and `[midimap]` lines name them).
- Every unit has `make test`; add a WAV render when the sound matters.
- A faceplate is optional: one self-contained HTML file, see `sdk/doc/faceplates.md`. It runs
  sandboxed and only talks to its own unit's parameters.

A unit that breaks these rules (a bad pointer, too much stack, a forbidden instruction) is
stopped and reported on the console, e.g. `pc ... [Tremolo+0x00c0]`; the offset is an address in
`units/<unit>/build/<cpu>/<name>.elf`: `aarch64-none-elf-addr2line -f -e <elf> 0xc0` (or
`arm-none-eabi-addr2line` for `arm32`). It stays off until the device reboots.

New unit: copy `units/tremolo/`, rename `NAME`, `BUNDLE`, the plugin entry function and the
plugin's `.name`. A plugin name is global on a device: don't reuse one from Essentials (`Utility`,
`EQ`, `Compressor`, `Delay`, `Filter`, `YAFR`) or another unit. `BUNDLE` becomes
`/units/<BUNDLE>.unt` on the card.

## Setups: the config language

Each `setups/<setup>/<player>.txt` is a whole `metalhead.txt` (the firmware reads it from the SD
card at boot). Each line can only name units declared above it, so `[units]` comes first and
`[buses]` before `[audioroutes]`. The sections:

- `[units]`: `<name> <Plugin>`, a plugin instance. Built-in plugins: `ClickTrack`, `Looper`,
  `MotionLight`, `Network`, `Bus`. Others come from unit files on the card: Essentials (free for
  everyone) and the ones in `units/`.
- `[buses]`: `<bus> [unit ...]`, a named stereo bus with an effect strip of `[units]` in series;
  `level` is its fader.
- `[audioroutes]`: `<source> <sink> [gain]`. Endpoints are `unit:channel`, `bus:channel` or
  `.Device_Name:channel` (a USB device by product name, spaces as `_`; `.device` is the computer).
- `[midiroutes]`: `<source> <sink>` (a unit or `.Device_Name`). USB mice, keyboards and joysticks
  are MIDI sources too, and a keyboard's LEDs a destination (metalhead-firmware's
  `ccs/system/src/usbdrivers/`).
- `[midimap]`: `[.Device:]cc41|noteon60|noteoff60 <unit>:<parameter>` or `preset:<name>`.
- `[usbdrivers]`: `.<device> <Driver>`.
- `[presets]`: `<preset> <unit>:<parameter> <0..127>`; `startup` is sent at boot.

**Never put a `[connect]` section in a setup.** It holds the device's own server key and console
settings; `check.py` refuses it. Device names in routes must match what the player's interface
reports; ask the player, or look at their device's config (`tools/console.py cfgget`).

## Working with others

When `project.json` has more than one player (a band), several people work here at once, each
with their own agent session:

- **Branch, then pull request.** Never push to `main`. Name the branch after the player and the
  change (`alice/gig-setup`). Pull before you start; another session may have changed what you
  are about to touch.
- **A player's file is theirs.** `setups/<setup>/<player>.txt` is what that player's device runs.
  Change another player's file only when that player asked, and say so in the PR. Shared changes
  (a new setup for everyone, a rename) go in one PR that every affected player reviews.
- **Say what it sounds like.** A PR describes the musical change (what each player hears, what
  moved where), not only the lines.

Alone, commit to `main` or use branches as you like; the checks are the same.

Never commit build output (`units/*/build/`, `dist/`), keys or tokens.
