"""Aligns the taps of a clips60 clip (GPU capture) with the video clock.

ffmpeg starts on Windows a while after `t0` (the emulator clock when it was launched), so the
measured `t` runs ahead of the video. First the offset is estimated with the first action
(preceded by stillness): first change of its area in [t - 4 s, t + 0.35 s]. Then, for each action,
the change of its area is searched near `t + offset` (+-0.3 s) and the median is taken.
The time the app takes to paint the response (REACTION) is subtracted from the corrected `t`.

Usage: python3 sync60.py <clip-name>
"""
import json
import re
import statistics
import subprocess
import sys

VID = "/PATH/TO/WORKDIR/clips60"
TOOLS = "/PATH/TO/WORKDIR/capture"
REACTION = 0.04
THRESHOLD = 1.5
WIDTH, HEIGHT = 1080, 2400


def area(e):
    if e["type"] == "tap":
        cx, cy, w, h = e["x"], e["y"], 320, 200
    else:
        cx, cy, w, h = (e["x"] + e["x2"]) // 2, (e["y"] + e["y2"]) // 2, 700, 500
    x = min(max(cx - w // 2, 0), WIDTH - w)
    y = min(max(cy - h // 2, 0), HEIGHT - h)
    return w, h, x, y


def differences(video, box):
    w, h, x, y = box
    output = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", video, "-vf",
         f"crop={w}:{h}:{x}:{y},tblend=all_mode=difference,signalstats,"
         "metadata=print:key=lavfi.signalstats.YAVG:file=-", "-f", "null", "-"],
        capture_output=True, text=True).stdout
    times = [float(m) for m in re.findall(r"pts_time:([0-9.]+)", output)]
    values = [float(m) for m in re.findall(r"YAVG=([0-9.]+)", output)]
    return list(zip(times, values))


name = sys.argv[1]
original = f"{TOOLS}/{name}.gpu-emulator-clock.json"
try:
    events = json.load(open(original))
except FileNotFoundError:
    events = json.load(open(f"{VID}/{name}.taps.json"))
    json.dump(events, open(original, "w"), indent=1)

video = f"{VID}/{name}.mp4"
series = [differences(video, area(e)) for e in events]

first = events[0]
# Changes in the area of the first action preceded by 0.4 s of stillness in that area (so the
# first frame of the video or an animation already running do not count); the closest to t.
series0 = series[0]
candidates = []
for i, (t, v) in enumerate(series0):
    if t < 0.5 or v <= THRESHOLD or not (first["t"] - 4.0 <= t <= first["t"] + 0.35):
        continue
    if all(vv <= THRESHOLD for tt, vv in series0[:i] if t - 0.4 <= tt < t):
        candidates.append(t)
if not candidates:
    raise SystemExit(f"{name}: the first action leaves no visible change to estimate the offset")
change = min(candidates, key=lambda c: abs(c - first["t"]))
estimated = change - first["t"]

diffs = []
for e, s in zip(events, series):
    center = e["t"] + estimated
    c = next((t for t, v in s if center - 0.3 <= t <= center + 0.3 and v > THRESHOLD), None)
    if c is not None:
        diffs.append(round(c - e["t"], 3))
offset = statistics.median(diffs) if diffs else estimated
for e in events:
    e["t"] = round(max(0.0, e["t"] + offset - REACTION), 3)
json.dump(events, open(f"{VID}/{name}.taps.json", "w"), ensure_ascii=False, indent=1)
print(f"{name}: offset {offset:+.3f} s (estimated with the first action {estimated:+.3f}); "
      f"{len(diffs)} of {len(events)} actions aligned {diffs}")
