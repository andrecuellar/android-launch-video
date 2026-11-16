"""Moves the times of a .taps.json to the video clock (screenrecord clips, see clip.py).

screenrecord takes a few tenths of a second to deliver its first frame after `START`, so the `t`
measured on the emulator runs ahead of the video. For each action the area of the screen it touches
(a box around the tap, or around the middle of the swipe) is watched in the video, and the first
frame where that area changes near `t` is searched. The clip offset is the median of (change - t)
of the actions found; the time the app takes to paint the response (REACTION) is also subtracted
from the corrected `t`. The final `t` is in seconds of the video.

Usage: python3 sync.py <clip-name>
"""
import json
import re
import statistics
import subprocess
import sys

VID = "/PATH/TO/WORKDIR/clips"
TOOLS = "/PATH/TO/WORKDIR/capture"
REACTION = 0.04
THRESHOLD = 1.5          # mean luminance difference between frames (0 to 255) inside the box
BEFORE, AFTER = 0.9, 0.35
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
original = f"{TOOLS}/{name}.taps-emulator-clock.json"
try:
    events = json.load(open(original))
except FileNotFoundError:
    events = json.load(open(f"{VID}/{name}.taps.json"))
    json.dump(events, open(original, "w"), indent=1)

video = f"{VID}/{name}.mp4"
diffs = []
for e in events:
    s = differences(video, area(e))
    change = next((t for t, v in s if e["t"] - BEFORE <= t <= e["t"] + AFTER and v > THRESHOLD), None)
    if change is not None:
        diffs.append(round(change - e["t"], 3))
if not diffs:
    raise SystemExit(f"{name}: no action can be aligned with the video")
offset = statistics.median(diffs)
for e in events:
    e["t"] = round(max(0.0, e["t"] + offset - REACTION), 3)
json.dump(events, open(f"{VID}/{name}.taps.json", "w"), ensure_ascii=False, indent=1)
print(f"{name}: offset {offset:+.3f} s with {len(diffs)} of {len(events)} actions {diffs}")
