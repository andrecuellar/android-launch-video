"""Difference sweep of a final MP4: sudden jumps, long freezes and the still stretch at the end.
Usage: venv/bin/python -I diffs.py <video.mp4>
"""
import subprocess, sys
import numpy as np
path = sys.argv[1]
w, h, fr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip().split(",")
w, h = int(w) // 4, int(h) // 4; n, d = map(int, fr.split("/")); fps = n / d
p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", f"scale={w}:{h}:flags=area", "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
prev, dif = None, []
while True:
    b = p.stdout.read(w * h)
    if len(b) < w * h: break
    f = np.frombuffer(b, dtype=np.uint8).astype(np.float32)
    dif.append(0.0 if prev is None else float(np.mean(np.abs(f - prev)))); prev = f
p.wait(); dif = np.array(dif); t = np.arange(len(dif)) / fps
print(f"{len(dif)} frames at {fps:g} fps ({len(dif) / fps:.2f} s)")
med = np.median(dif[1:])
peaks = sorted(range(1, len(dif)), key=lambda i: -dif[i])[:12]
print("largest changes between frames (mean diff 0-255; film median %.2f):" % med)
for i in sorted(peaks): print(f"  {t[i]:6.3f} s  {dif[i]:6.2f}")
# freezes: stretches of >= 0.25 s without changes beyond the grain (diff < 0.35)
still, start = [], None
for i in range(1, len(dif)):
    if dif[i] < 0.35:  # the grain changes every 1/12 s: below this the image is still
        if start is None: start = i
    else:
        if start is not None and (i - start) / fps >= 0.25: still.append((t[start], t[i - 1]))
        start = None
if start is not None: still.append((t[start], t[-1]))
print("still stretches of 0.25 s or more:", ", ".join(f"{a:.2f}-{b:.2f}" for a, b in still) or "none")
