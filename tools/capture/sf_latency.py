"""Reads the presentation times of the app layer (dumpsys SurfaceFlinger --latency) right after a
swipe and measures the intervals between presented frames.

Usage: PACKAGE=<app package> python3 sf_latency.py <x> <y1> <y2> <ms>"""
import os, subprocess, sys, statistics
sys.path.insert(0, "/PATH/TO/WORKDIR")
from kitconfig import cfg  # noqa: E402
A = ["adb", "-s", cfg("emulator_serial"), "shell"]
layers = subprocess.run(A + ["dumpsys SurfaceFlinger --list"], capture_output=True, text=True).stdout
name = next(l for l in layers.splitlines() if os.environ["PACKAGE"] in l and "(BLAST)" in l)  # PACKAGE=<package>; in Flutter it is the SurfaceView[...] layer
name = name.split("{", 1)[1].split(" parentId")[0].split(" ", 1)[1]
subprocess.run(A + [f"dumpsys SurfaceFlinger --latency-clear '{name}'"], capture_output=True)
x, y1, y2, ms = sys.argv[1:5]
subprocess.run(A + [f"input swipe {x} {y1} {x} {y2} {ms}"])
subprocess.run(["sleep", "1.6"])
out = subprocess.run(A + [f"dumpsys SurfaceFlinger --latency '{name}'"], capture_output=True, text=True).stdout.split()
period = int(out[0])
rows = [tuple(map(int, out[i:i + 3])) for i in range(1, len(out) - 2, 3)]
presented = sorted(f[1] for f in rows if 0 < f[1] < 2**62)
ints = [(b - a) / 1e6 for a, b in zip(presented, presented[1:])]
# Only the stretch with consecutive frames (motion): gaps over 300 ms split stretches.
run, runs = [], []
for i in ints:
    if i > 300:
        if run: runs.append(run)
        run = []
    else:
        run.append(i)
if run: runs.append(run)
mov = max(runs, key=len) if runs else []
print(f"layer: {name}\nrefresh period: {period/1e6:.2f} ms, presented frames: {len(presented)}")
if mov:
    print(f"in motion: {len(mov)+1} frames, {1000/statistics.mean(mov):.1f} fps, max {max(mov):.1f} ms, "
          f">20 ms: {sum(i>20 for i in mov)}, >35 ms: {sum(i>35 for i in mov)}")
