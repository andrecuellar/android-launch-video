#!/usr/bin/env bash
# Prepares the 60 fps recordings when they arrive: frames, times, motion and a summary of the taps.
# Usage: clips60.sh [clips_folder=../clips60]. Writes to video/material60/ (the old material stays).
set -euo pipefail
V=/PATH/TO/WORKDIR/video
VID=${1:-$V/../clips60}
PY=$V/../venv/bin/python
mkdir -p $V/material60
$PY -I $V/scripts/clips.py "$VID" $V/material60
$PY -I $V/scripts/motion.py $V/material60
python3 - "$V/material60" <<'PY'
import json, os, sys
m = sys.argv[1]
txt = open(os.path.join(m, "clips.js")).read(); C = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
M = json.load(open(os.path.join(m, "motion.json")))
for clip, c in sorted(C.items()):
    print(f"\n{clip}: {c['n']} frames, {c['duration']:.2f} s")
    for k in c["taps"]:
        print(f"  {k['type']:9s} t {k['t']:6.3f}  ({k['x']},{k['y']})" + (f" -> ({k['x2']},{k['y2']}) {k['ms']} ms" if k['type'] != 'tap' else ""))
    print("  motion: " + ", ".join(f"{a:.2f}-{b:.2f}" for a, b in M[clip]["motion"]))
PY
