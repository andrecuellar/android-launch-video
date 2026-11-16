"""Stutter detector on the phone screen of an already rendered MP4.

Usage: [MATERIAL=<material_folder>] venv/bin/python -I stutter.py <video.mp4> <screens.json> [from] [to] [offset]
(from and to in film time; offset = film time at the first frame of the video)
screens.json comes from screens.mjs (same format and same version of the film). For every frame it
crops the screen (its four corners, with rotation and tilt), resamples it to a fixed grid (so the
camera does not count as motion) and measures the difference with the previous frame: the largest,
over tiles, of the mean |diff| in 0-255. A stutter is, inside a span with motion, two or more nearly
equal frames followed by a large jump. With MATERIAL set, each stutter is also classified by cause.
"""
import json, subprocess, sys
import numpy as np
from scipy.ndimage import map_coordinates

path, P = sys.argv[1], json.load(open(sys.argv[2]))
start = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
end = float(sys.argv[4]) if len(sys.argv) > 4 else 1e9
offset = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
W, H, fps, Q = P["W"], P["H"], P["fps"], P["frames"]
info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0", path],
                      capture_output=True, text=True).stdout.strip().split(",")
vw, vh = int(info[0]), int(info[1]); num, den = map(int, info[2].split("/")); vfps = num / den
RED = 2  # the video is read at half size (area average): grain and compression noise fade out
lw, lh = vw // RED, vh // RED
sc = lw / W
GX, GY = 64, 144  # grid inside the screen (5 % margin), 8 x 8 tiles
u = np.linspace(0.05, 0.95, GX); v = np.linspace(0.05, 0.95, GY)
U, V = np.meshgrid(u, v)
def diff(a, b):
    return float(np.abs(a - b).reshape(GY // 8, 8, GX // 8, 8).mean(axis=(1, 3)).max())
proc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", f"scale={lw}:{lh}:flags=area", "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
prev, series, i = None, [], 0
while True:
    buf = proc.stdout.read(lw * lh)
    if len(buf) < lw * lh: break
    t = i / vfps + offset; i += 1
    q = Q[min(len(Q) - 1, int(round(t * fps)))]
    if not q["q"] or t < start or t > end:
        prev = None; series.append(None); continue
    img = np.frombuffer(buf, dtype=np.uint8).reshape(lh, lw).astype(np.float32)
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = q["q"]
    # bilinear between the four corners (enough for the slight perspective)
    X = ((1 - V) * ((1 - U) * x0 + U * x1) + V * ((1 - U) * x3 + U * x2)) * sc
    Y = ((1 - V) * ((1 - U) * y0 + U * y1) + V * ((1 - U) * y3 + U * y2)) * sc
    m = map_coordinates(img, [Y, X], order=1, mode="nearest")
    series.append(None if prev is None else diff(m, prev))
    prev = m
proc.wait()
STILL, found = 0.6, []
for j in range(3, len(series) - 3):
    d = series[j]
    if d is None or series[j - 1] is None or series[j - 2] is None: continue
    if not (series[j - 1] < STILL and series[j - 2] < STILL): continue
    near = [x for x in series[max(0, j - 10):j - 2] + series[j + 1:j + 9] if x is not None]
    mov = [x for x in near if x >= STILL]
    if len(mov) < 4: continue  # not a span with motion
    typical = float(np.median(mov))
    if d > max(3.0, 1.6 * typical):
        found.append((j / vfps + offset, d, typical))
measured = sum(1 for x in series if x is not None)
# Classification: from the edit (the map freezes or jumps) or from the recording (the emulator repeated frames).
import os, json, bisect
MAT = os.environ.get("MATERIAL")
if MAT:
    txt = open(os.path.join(MAT, "clips.js")).read(); CL = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
    MV = json.load(open(os.path.join(MAT, "motion.json")))
def idx(clip, tc):
    ts = CL[clip]["times"]; return max(0, bisect.bisect_right(ts, tc + 1e-6) - 1)
def cause(tt):
    if not MAT: return ""
    k = int(round(tt * fps))
    if k < 3 or k >= len(Q): return "no data"
    q = [Q[k - 3], Q[k - 2], Q[k - 1], Q[k]]
    if any(x.get("fade") for x in q): return "crossfade between shots"
    if any(not x.get("clip") for x in q) or len({x["clip"] for x in q}) > 1: return "shot change"
    tcs = [x["tc"] for x in q]; dt = [tcs[i + 1] - tcs[i] for i in range(3)]
    if any(d > 0.05 or d < -1e-6 for d in dt): return "EDIT: map jump"
    if any(abs(d) < 1e-6 for d in dt[:2]): return "EDIT: map freeze"
    clip = q[0]["clip"]; ids = [idx(clip, tc) for tc in tcs]
    rep = [MV[clip]["d"][i] < 0.6 for i in ids[1:3] if 0 < i < len(MV[clip]["d"])]
    return "recording (the emulator repeated the frame)" if any(rep) else "recording (frame recorded with an irregular step)"
print(f"frames measured: {measured} of {len(series)}; stutters: {len(found)}")
count = {}
for t, s, mv in found:
    c = cause(t); count[c] = count.get(c, 0) + 1
    print(f"  {t:7.3f} s  jump {s:6.1f}  (typical neighbor step {mv:.1f})  {c}")
if MAT: print("by cause:", ", ".join(f"{k}: {v}" for k, v in count.items()) or "none")
