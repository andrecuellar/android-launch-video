"""Motion of every recording: difference between consecutive frames and the spans with motion.

Usage: venv/bin/python -I motion.py <material_folder> [clip ...]
       venv/bin/python -I motion.py <material_folder> --compare <clipA> <tA> <clipB> <tB>
Reads material/clips.js and material/frames/<clip>/ and writes material/motion.json:
{clip: {"d": [diff with the previous frame], "motion": [[t0, t1], ...], "threshold": 2.0}}.
The difference is the largest, over 34x38 px tiles (at 1/4 scale), of the mean |diff| in 0-255:
that way a digit that changes counts even when the rest of the screen is still. Outside the spans
with motion the screen is still and a time jump is not noticeable.
"""
import json, os, subprocess, sys
import numpy as np

mat = sys.argv[1]
txt = open(os.path.join(mat, "clips.js")).read()
CLIPS = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
THRESHOLD = 2.0
W, H, TILES = 272, 608, (16, 8)  # 16 rows x 8 columns of 34 x 38 tiles

def grays(clip, start=0, count=None):
    n = CLIPS[clip]["n"] if count is None else count
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-start_number", str(start), "-i", os.path.join(mat, "frames", clip, "%05d.jpg"),
                          "-frames:v", str(n), "-vf", f"scale={W}:{H}:flags=area", "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H)
        if len(b) < W * H: break
        yield np.frombuffer(b, dtype=np.uint8).reshape(H, W).astype(np.float32)
    p.wait()

def diff(a, b):
    m = np.abs(a - b).reshape(TILES[0], H // TILES[0], TILES[1], W // TILES[1]).mean(axis=(1, 3))
    return float(m.max())

def index(clip, t):
    ts = CLIPS[clip]["times"]
    i = int(np.searchsorted(ts, t + 1e-6, side="right")) - 1
    return max(0, min(i, CLIPS[clip]["n"] - 1))

if len(sys.argv) > 2 and sys.argv[2] == "--compare":
    ca, ta, cb, tb = sys.argv[3], float(sys.argv[4]), sys.argv[5], float(sys.argv[6])
    a = next(grays(ca, index(ca, ta), 1)); b = next(grays(cb, index(cb, tb), 1))
    print(f"{ca} {ta} (frame {index(ca, ta)}) vs {cb} {tb} (frame {index(cb, tb)}): diff {diff(a, b):.2f} (threshold {THRESHOLD})")
    sys.exit(0)

requested = sys.argv[2:] or sorted(CLIPS)
json_path = os.path.join(mat, "motion.json")
out = json.load(open(json_path)) if os.path.exists(json_path) else {}
for clip in requested:
    c = CLIPS[clip]; ts = c["times"]
    prev, d = None, []
    for g in grays(clip):
        d.append(0.0 if prev is None else round(diff(g, prev), 2))
        prev = g
    n = len(d)
    mov = []
    for i in range(1, n):
        if d[i] <= THRESHOLD: continue
        if mov and ts[i] - mov[-1][1] < 0.15: mov[-1][1] = ts[i]
        else: mov.append([max(ts[i - 1], ts[i] - 0.034), ts[i]])  # with VFR the change arrives with its frame
    mov = [[round(a, 3), round(b, 3)] for a, b in mov]
    out[clip] = {"d": d, "motion": mov, "threshold": THRESHOLD}
    dt = np.diff(ts) if len(ts) > 1 else np.array([0])
    rep = sum(1 for i in range(1, n) if d[i] <= 0.4 and any(a <= ts[i] <= b for a, b in mov))
    print(f"{clip}: {n} frames, median step {np.median(dt)*1000:.1f} ms, max {dt.max()*1000:.0f} ms; repeated frames inside a motion: {rep}")
    print("  motion: " + ", ".join(f"{a:.2f}-{b:.2f}" for a, b in mov))
json.dump(out, open(json_path, "w"))
