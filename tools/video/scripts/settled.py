"""For jumps inside still spans: from when the screen already equals the target frame.
Usage: settled.py <material> "<clip> <a> <b>" ...  -> first t in [a, b] from which every frame up
to b differs <= 1.5 from the frame at b (jumping from any t after it to b is not noticeable)."""
import os, sys
args = sys.argv[2:]
sys.argv = [sys.argv[0], sys.argv[1], "--compare"]
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "motion.py")).read()
src = src[:src.index('if len(sys.argv) > 2 and sys.argv[2] == "--compare":')]
g = {}; exec(compile(src, "motion.py", "exec"), g)
CLIPS, diff, index, grays = g["CLIPS"], g["diff"], g["index"], g["grays"]
for a in args:
    clip, ta, tb = a.split(); ta, tb = float(ta), float(tb)
    ia, ib = index(clip, ta), index(clip, tb)
    F = list(grays(clip, ia, ib - ia + 1)); ref = F[-1]; ts = CLIPS[clip]["times"]
    d = [diff(f, ref) for f in F]
    k = len(d) - 1
    while k > 0 and d[k - 1] <= 1.5: k -= 1
    print(f"{clip} {ta:.2f}-{tb:.2f}: equal to the end from {ts[ia + k]:.3f} (diff at {ta:.2f}: {d[0]:.1f})")
