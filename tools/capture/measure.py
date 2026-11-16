"""Measures the smoothness of a video while there is motion.

For each frame it computes how much the content area changed from the previous one (mean
luminance difference). A "new" frame is one that changes more than THRESHOLD. New frames are
grouped into motion runs (gaps up to CUT s); in each run the intervals between new frames are
measured: mean fps, maximum interval and how many exceed 20 ms and 35 ms.
It also reports the container rate (all frames, changing or not).

Usage: python3 measure.py <video> [threshold] [y0:y1] [cut]
"""
import re
import statistics
import subprocess
import sys

video = sys.argv[1]
THRESHOLD = float(sys.argv[2]) if len(sys.argv) > 2 else 0.25
zone = sys.argv[3] if len(sys.argv) > 3 else None
CUT = float(sys.argv[4]) if len(sys.argv) > 4 else 0.6
MIN_FRAMES = 8

width, height = map(int, subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height",
     "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip().split(",")[:2])
if zone:
    y0, y1 = (int(v) for v in zone.split(":"))
else:
    # The content area: without the status bar or the app's navigation bar.
    y0, y1 = int(height * 0.12), int(height * 0.86)
vfilter = (f"crop={width}:{y1 - y0}:0:{y0},tblend=all_mode=difference,signalstats,"
           "metadata=print:key=lavfi.signalstats.YAVG:file=-")
output = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", vfilter, "-f", "null", "-"],
                        capture_output=True, text=True).stdout
times = [float(m) for m in re.findall(r"pts_time:([0-9.]+)", output)]
values = [float(m) for m in re.findall(r"YAVG=([0-9.]+)", output)]
series = list(zip(times, values))

all_frames = [float(x.split(",")[0]) for x in subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "frame=pts_time",
     "-of", "csv=p=0", video], capture_output=True, text=True).stdout.split() if x.split(",")[0].strip()]
container_ints = [b - a for a, b in zip(all_frames, all_frames[1:])]

new = [t for t, v in series if v > THRESHOLD]
runs, current = [], []
for t in new:
    if current and t - current[-1] > CUT:
        runs.append(current)
        current = []
    current.append(t)
if current:
    runs.append(current)
runs = [r for r in runs if len(r) >= MIN_FRAMES]

print(f"{video.rsplit('/', 1)[-1]}: {width}x{height}, {len(all_frames)} frames in the container, "
      f"mean container interval {statistics.mean(container_ints) * 1000:.1f} ms")
total = []
for i, r in enumerate(runs, 1):
    ints = [b - a for a, b in zip(r, r[1:])]
    total += ints
    dur = r[-1] - r[0]
    print(f"  run {i}: {r[0]:.2f}-{r[-1]:.2f} s, {len(r)} new frames, "
          f"{(len(r) - 1) / dur:.1f} fps, max {max(ints) * 1000:.0f} ms, "
          f">20 ms: {sum(x > 0.020 for x in ints)}, >35 ms: {sum(x > 0.035 for x in ints)}")
if total:
    print(f"  TOTAL in motion: {1 / statistics.mean(total):.1f} fps, max {max(total) * 1000:.0f} ms, "
          f">20 ms: {sum(x > 0.020 for x in total)} of {len(total)}, >35 ms: {sum(x > 0.035 for x in total)}")
else:
    print("  no motion runs")
