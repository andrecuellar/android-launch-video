"""Period of a looping animation inside a region of the recording (e.g. a Lottie inside a sheet).

Usage: venv/bin/python -I period.py <material_folder> <clip> <t0> <t1> <y0> <y1> [x0 x1]
Compares the region (native 1080x2400 coordinates) between frames tau apart and looks for the tau
that repeats it: a time jump of k times that period is not noticeable in the animation.
"""
import json, os, subprocess, sys
import numpy as np
mat, clip = sys.argv[1], sys.argv[2]
t0, t1, y0, y1 = map(float, sys.argv[3:7])
x0, x1 = (float(sys.argv[7]), float(sys.argv[8])) if len(sys.argv) > 8 else (0, 1080)
txt = open(os.path.join(mat, "clips.js")).read(); C = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
ts = np.array(C[clip]["times"]); n = C[clip]["n"]
W, H = 270, 600
p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-start_number", "0", "-i", os.path.join(mat, "frames", clip, "%05d.jpg"), "-frames:v", str(n),
                      "-vf", f"scale={W}:{H}:flags=area", "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
F = []
while True:
    b = p.stdout.read(W * H)
    if len(b) < W * H: break
    F.append(np.frombuffer(b, dtype=np.uint8).reshape(H, W)[int(y0 / 4):int(y1 / 4), int(x0 / 4):int(x1 / 4)].astype(np.float32))
F = np.array(F)
def frame_at(t): return F[max(0, int(np.searchsorted(ts, t + 1e-6, side="right")) - 1)]
best = []
for tau in np.arange(0.3, min(6.0, t1 - t0), 0.01):
    ds = [np.mean(np.abs(frame_at(t) - frame_at(t + tau))) for t in np.arange(t0, t1 - tau, 0.05)]
    best.append((float(np.mean(ds)), round(float(tau), 2)))
best.sort()
print("best tau (mean diff, tau):", best[:8])
