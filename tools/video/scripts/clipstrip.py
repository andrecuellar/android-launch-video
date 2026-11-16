"""Strip of frames of a clip at the requested times, with the time written on each one.
Usage: clipstrip.py <material> <clip> <out.png> t1 t2 ..."""
import json, os, subprocess, sys, bisect
mat, clip, out = sys.argv[1:4]; ts = [float(x) for x in sys.argv[4:]]
txt = open(os.path.join(mat, "clips.js")).read(); C = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
T = C[clip]["times"]
# Any .ttf in film/assets works: this one is tried first, then the first .ttf found there.
font = "/PATH/TO/WORKDIR/video/film/assets/IBMPlexSans-SemiBold.ttf"
if not os.path.exists(font):
    import glob; font = sorted(glob.glob(os.path.dirname(font) + "/*.ttf"))[0]
inputs, filters = [], []
for k, t in enumerate(ts):
    i = max(0, bisect.bisect_right(T, t + 1e-6) - 1)
    inputs += ["-i", os.path.join(mat, "frames", clip, f"{i:05d}.jpg")]
    filters.append(f"[{k}]scale=270:600,drawtext=fontfile={font}:text='{t:.2f}':x=8:y=8:fontsize=26:fontcolor=white:box=1:boxcolor=black@0.6[v{k}]")
filters.append("".join(f"[v{k}]" for k in range(len(ts))) + f"hstack=inputs={len(ts)}")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters), out], check=True)
print(out)
