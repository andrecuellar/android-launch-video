"""Copies the recording frame shown at a time into <material>/keyframes/<name>.jpg.
Usage: keyframe.py <material> <clip>:<t>:<name> ...  (the keyframes folder must exist)"""
import json, os, sys, bisect, shutil
material = sys.argv[1]
txt = open(os.path.join(material, "clips.js")).read()
C = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
for pair in sys.argv[2:]:
    clip, t, name = pair.split(":")
    c = C[clip]; i = max(0, bisect.bisect_right(c["times"], float(t)) - 1)
    src = os.path.join(material, "frames", clip, f"{i:05d}.jpg")
    shutil.copy(src, os.path.join(material, "keyframes", name + ".jpg"))
    print(name, clip, t, "-> frame", i, "pts", c["times"][i])
