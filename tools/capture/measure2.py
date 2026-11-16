"""Smoothness of a video while there is motion, frame by frame.

A frame "changes" if the mean luminance difference with the previous one in the content area is
above SOME. Changing frames are grouped into motion runs, split at gaps longer than CUT s; only
runs of at least MIN frames count (swipes, sheets sliding up), not isolated changes (a button
appearing). Inside each run the intervals between changing frames are measured. It also warns
about gaps between runs shorter than 0.3 s with strong motion on both sides: those would be
hitches in the middle of a movement.

Usage: python3 measure2.py <video> [y0:y1]
"""
import re
import statistics
import subprocess
import sys

video = sys.argv[1]
zone = sys.argv[2] if len(sys.argv) > 2 else None
SOME, STRONG, CUT, MIN = 0.25, 3.0, 0.1, 12

width, height = map(int, subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height",
     "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip().split(",")[:2])
y0, y1 = (int(v) for v in zone.split(":")) if zone else (int(height * 0.12), int(height * 0.86))
output = subprocess.run(
    ["ffmpeg", "-v", "error", "-i", video, "-vf",
     f"crop={width}:{y1 - y0}:0:{y0},tblend=all_mode=difference,signalstats,"
     "metadata=print:key=lavfi.signalstats.YAVG:file=-", "-f", "null", "-"],
    capture_output=True, text=True).stdout
series = list(zip([float(m) for m in re.findall(r"pts_time:([0-9.]+)", output)],
                  [float(m) for m in re.findall(r"YAVG=([0-9.]+)", output)]))
value = dict(series)
changes = [t for t, v in series if v > SOME]
runs, current = [], []
for t in changes:
    if current and t - current[-1] > CUT:
        runs.append(current)
        current = []
    current.append(t)
if current:
    runs.append(current)
long_runs = [r for r in runs if len(r) >= MIN]

total = []
print(f"{video.rsplit('/', 1)[-1]}: {width}x{height}")
for i, r in enumerate(long_runs, 1):
    ints = [b - a for a, b in zip(r, r[1:])]
    total += ints
    print(f"  run {i}: {r[0]:.2f}-{r[-1]:.2f} s, {len(r)} frames, {(len(r) - 1) / (r[-1] - r[0]):.1f} fps, "
          f"max {max(ints) * 1000:.0f} ms, >20 ms: {sum(x > 0.020 for x in ints)}, >35 ms: {sum(x > 0.035 for x in ints)}")
hitches = []
for a, b in zip(runs, runs[1:]):
    gap = b[0] - a[-1]
    if gap < 0.3 and value.get(a[-1], 0) > STRONG and value.get(b[0], 0) > STRONG:
        hitches.append(gap)
if total:
    print(f"  TOTAL: {1 / statistics.mean(total):.1f} fps, max {max(total) * 1000:.0f} ms, "
          f">20 ms: {sum(x > 0.020 for x in total)} of {len(total)}, >35 ms: {sum(x > 0.035 for x in total)}"
          f"; hitches in motion: {len(hitches)} {[round(x * 1000) for x in hitches]}")
else:
    print("  no motion runs")
# Core of the motion: inside each run, from the first to the last frame with a strong change
# (without the braking tail or the isolated changes after it).
core = []
for r in long_runs:
    strong = [t for t in r if value.get(t, 0) > STRONG]
    if len(strong) < 2:
        continue
    inside = [t for t in r if strong[0] <= t <= strong[-1]]
    core += [b - a for a, b in zip(inside, inside[1:])]
if core:
    print(f"  CORE: {1 / statistics.mean(core):.1f} fps, max {max(core) * 1000:.0f} ms, "
          f">20 ms: {sum(x > 0.020 for x in core)} of {len(core)}, >35 ms: {sum(x > 0.035 for x in core)}")
