#!/usr/bin/env python3
"""Collects the built unit files into dist/<machine>-<Bundle>.unt (flat, as release assets) and writes
dist/units.json: for each unit its bundle name, plugins and, per machine (arm32: the BeagleBone
Black; aarch64: the Raspberry Pi 4 and 5), the boards, size and sha256, plus the commit they were
built from. Run from units/ (make dist) after make.

    python3 ../tools/dist.py <unit dir> ...
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

BOARDS = {"arm32": ["bbb"], "aarch64": ["rpi4", "rpi5"]}


def variable(makefile, name):
    m = re.search(rf"^{name}\s*:?=\s*(\S+)", makefile, re.M)
    return m.group(1) if m else None


def main(units):
    root = Path.cwd()
    dist = root.parent / "dist"
    shutil.rmtree(dist, ignore_errors=True)
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    out = {"commit": commit, "units": []}
    for u in units:
        makefile = (root / u / "Makefile").read_text()
        name, bundle = variable(makefile, "NAME"), variable(makefile, "BUNDLE")
        plugins = []
        for src in sorted((root / u).glob("*.c*")):
            plugins += re.findall(r'\.name\s*=\s*"([^"]+)"', src.read_text(errors="replace"))
        files = {}
        for machine, boards in BOARDS.items():
            built = root / u / "build" / machine / f"{name}.unt"
            if not built.exists():
                continue
            target = dist / f"{machine}-{bundle}.unt"
            dist.mkdir(exist_ok=True)
            shutil.copyfile(built, target)
            data = target.read_bytes()
            files[machine] = {"boards": boards, "path": target.name, "size": len(data),
                              "sha256": hashlib.sha256(data).hexdigest()}
        out["units"].append({"unit": u, "bundle": bundle, "plugins": plugins, "files": files})
    dist.mkdir(exist_ok=True)
    (dist / "units.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"dist/units.json: {len(out['units'])} unit{'s' if len(out['units']) != 1 else ''}")


if __name__ == "__main__":
    main(sys.argv[1:])
