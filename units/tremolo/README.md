# Tremolo

Amplitude modulation for a stereo pair. With `division` set, it locks to the transport (the
room's timeline on metalhead.link), so everyone's tremolo pulses on the same beat.

| Parameter | Range | |
|---|---|---|
| `rate` | 0.1–20 Hz | the LFO when free running or with no transport |
| `depth` | 0–100 % | 0 is off |
| `division` | free, 1/4, 1/8, 1/16, 1/8T | cycles per note when synced |
| `shape` | 0–100 % | sine at 0, towards a square at 100 |

Light enough for the BeagleBone Black: one `sinf` and two `tanhf` per sample frame.
