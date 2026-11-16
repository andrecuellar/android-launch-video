"""Draws rectangles (native coordinates) over frames of a clip, to check crops.
Usage: rects.py <material> <out.png> "<clip>@<t>:x,y,w,h;x,y,w,h" ...  (each argument is one panel)"""
import json, os, subprocess, sys, bisect
mat, out = sys.argv[1:3]
txt = open(os.path.join(mat, "clips.js")).read(); C = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
inputs, filters = [], []
for k, arg in enumerate(sys.argv[3:]):
    head, rs = arg.split(":")
    clip, t = head.split("@"); t = float(t)
    T = C[clip]["times"]; i = max(0, bisect.bisect_right(T, t + 1e-6) - 1)
    inputs += ["-i", os.path.join(mat, "frames", clip, f"{i:05d}.jpg")]
    rects = [r for r in rs.split(";") if r]
    f = f"[{k}]" + (",".join(f"drawbox=x={c.split(',')[0]}:y={c.split(',')[1]}:w={c.split(',')[2]}:h={c.split(',')[3]}:color=red@0.9:t=5" for c in rects) or "null") + f",scale=360:800[v{k}]"
    filters.append(f)
n = len(sys.argv) - 3
filters.append("".join(f"[v{k}]" for k in range(n)) + f"hstack=inputs={n}")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters), out], check=True)
print(out)
