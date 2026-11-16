"""Time-named links for the contact sheet of a clip: the last frame with pts <= t.
Usage: clipsheet.py <material> <clip> <step_s> <dest_folder>  (then sheet.mjs on <dest_folder>)
Besides every step, it adds the times 0.1 s and 0.35 s after each tap. Empties <dest_folder> first."""
import json, os, sys, bisect
material, clip, step, dest = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
txt = open(os.path.join(material, "clips.js")).read()
C = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])[clip]
os.makedirs(dest, exist_ok=True)
for f in os.listdir(dest): os.remove(os.path.join(dest, f))
t = 0.0
extra = [k["t"] for k in C["taps"]]
times = sorted(set([round(i * step, 3) for i in range(int(C["duration"] / step) + 2)] + [round(e + d, 3) for e in extra for d in (0.1, 0.35)]))
for t in times:
    i = max(0, bisect.bisect_right(C["times"], t) - 1)
    os.symlink(os.path.join(material, "frames", clip, f"{i:05d}.jpg"), os.path.join(dest, f"c-t{t:07.3f}.jpg"))
print(clip, len(times))
