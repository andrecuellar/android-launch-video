"""When a recording reaches a still state (to jump without it being noticed).
Usage: still.py <material> <clip> <a> <b>  -> diff of every frame in [a, b] with the frame at b and at a
       still.py <material> <clipA> <tA0> <tA1> <clipB> <tB>  -> diff of every frame of A in [tA0, tA1] with B at tB
"""
import os, sys
sys.argv = [sys.argv[0], sys.argv[1], "--compare"] + sys.argv[2:]
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "motion.py")).read()
src = src[:src.index('if len(sys.argv) > 2 and sys.argv[2] == "--compare":')]
g = {}; exec(compile(src, "motion.py", "exec"), g)
CLIPS, diff, index, grays = g["CLIPS"], g["diff"], g["index"], g["grays"]
a = sys.argv[3:]
if len(a) == 3:
    clip, t0, t1 = a[0], float(a[1]), float(a[2]); clipB, tB = clip, t1
else:
    clip, t0, t1, clipB, tB = a[0], float(a[1]), float(a[2]), a[3], float(a[4])
i0, i1 = index(clip, t0), index(clip, t1)
ref = next(grays(clipB, index(clipB, tB), 1)); ref0 = next(grays(clip, i0, 1))
ts = CLIPS[clip]["times"]
row = []
for k, f in enumerate(grays(clip, i0, i1 - i0 + 1)):
    row.append((ts[i0 + k], diff(f, ref), diff(f, ref0)))
print(f"{clip} {t0}-{t1} against {clipB} {tB} (and against the first one):")
print("  " + "  ".join(f"{t:.3f}:{d:.1f}/{e:.1f}" for t, d, e in row))
