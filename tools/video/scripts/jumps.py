"""Check of jumps and freezes on the phone screen, from the time maps.

Usage: venv/bin/python -I jumps.py <material_folder> <screens.json>
For every output frame (screens.mjs) it knows which frame of which recording is shown, and warns:
  frozen:  the map stops the clip while the recording is moving;
  jump:    the map jumps in time (or changes shot without a crossfade) and the screen visibly changes;
  stutter: two or more equal output frames inside a motion followed by a jump of two or more
           recording frames (the definition used by the final check).
"""
import json, os, sys
import numpy as np
sys.argv = [sys.argv[0], sys.argv[1], "--compare"] + sys.argv[2:]  # reuse the functions without running the main part
mat, path = sys.argv[1], sys.argv[3]
import importlib.util
spec = importlib.util.spec_from_file_location("mov", os.path.join(os.path.dirname(__file__), "motion.py"))
src = open(spec.origin).read(); src = src[:src.index('if len(sys.argv) > 2 and sys.argv[2] == "--compare":')]
mov = {}; exec(compile(src, spec.origin, "exec"), mov)
CLIPS, diff, index, grays, THRESHOLD = mov["CLIPS"], mov["diff"], mov["index"], mov["grays"], mov["THRESHOLD"]
MOV = json.load(open(os.path.join(mat, "motion.json")))
P = json.load(open(path)); fps = P["fps"]; Q = P["frames"]
cache = {}
def frame(clip, i):
    k = (clip, i)
    if k not in cache: cache[k] = next(grays(clip, i, 1))
    return cache[k]
def in_motion(clip, t):
    return any(a + 0.02 < t < b - 0.02 for a, b in MOV[clip]["motion"])
warnings = []
run = 0  # consecutive output frames with the same recording frame inside a motion
for k in range(1, len(Q)):
    a, b = Q[k - 1], Q[k]; t = k / fps
    if not a["clip"] or not b["clip"]: run = 0; continue
    ia, ib = index(a["clip"], a["tc"]), index(b["clip"], b["tc"])
    if b["fade"]: run = 0; continue
    if a["shot"] != b["shot"] or a["clip"] != b["clip"]:
        d = diff(frame(a["clip"], ia), frame(b["clip"], ib))
        if d > THRESHOLD: warnings.append((t, "jump", f"shot change without a crossfade: {a['clip']} {a['tc']:.3f} -> {b['clip']} {b['tc']:.3f}, diff {d:.1f}"))
        run = 0; continue
    dtc = b["tc"] - a["tc"]
    if abs(dtc) > 0.1 or dtc < -1e-6:
        if b.get("hidden"): run = 0; continue  # the jump stays under a replica (declared in the shot)
        d = diff(frame(a["clip"], ia), frame(b["clip"], ib))
        # inside a motion, a jump the size of a normal step is not noticeable
        loc = 0.0
        for k0, k1 in ((k - 2, k - 1), (k, k + 1)):
            if 0 <= k0 and k1 < len(Q) and Q[k0]["clip"] == Q[k1]["clip"] and Q[k0]["clip"] and abs(Q[k1]["tc"] - Q[k0]["tc"]) < 0.1:
                loc = max(loc, diff(frame(Q[k0]["clip"], index(Q[k0]["clip"], Q[k0]["tc"])), frame(Q[k1]["clip"], index(Q[k1]["clip"], Q[k1]["tc"]))))
        if d > max(THRESHOLD, 1.3 * loc): warnings.append((t, "jump", f"{b['clip']} {a['tc']:.3f} -> {b['tc']:.3f}, diff {d:.1f} (neighbor step {loc:.1f})"))
        run = 0; continue
    if abs(dtc) < 1e-6 and in_motion(b["clip"], b["tc"]):
        warnings.append((t, "frozen", f"{b['clip']} stopped at {b['tc']:.3f} while the recording is moving"))
    if ib == ia and in_motion(b["clip"], b["tc"]): run += 1
    else:
        if run >= 2 and ib - ia >= 2:
            warnings.append((t, "stutter", f"{b['clip']}: {run} equal frames and a jump of {ib - ia} frames at {b['tc']:.3f}"))
        run = 0
# Informative: frames that the recording itself repeats inside a motion (the emulator did not paint a
# new one). The edit does not add them: they show as they are and are only reported.
repeats = []
for k in range(1, len(Q)):
    a, b = Q[k - 1], Q[k]
    if not b["clip"] or b["fade"] or a["clip"] != b["clip"] or abs((b["tc"] - a["tc"]) - 1 / fps) > 0.004: continue
    i = index(b["clip"], b["tc"]); dd = MOV[b["clip"]]["d"]
    if 0 < i < len(dd) and dd[i] < 0.6 and in_motion(b["clip"], b["tc"]): repeats.append(k / fps)
groups = []
for t in repeats:
    if groups and t - groups[-1][1] < 0.1: groups[-1][1] = t; groups[-1][2] += 1
    else: groups.append([t, t, 1])
print(f"frames repeated by the recording inside a motion (reported only): {len(repeats)}"
      + (" in " + ", ".join(f"{a:.2f}-{b:.2f} ({n})" for a, b, n in groups) if groups else ""))
# group consecutive freezes
out, last = [], None
for t, kind, txt in warnings:
    if kind == "frozen" and last and last[1] == "frozen" and t - last[2] < 0.03:
        last[2] = t; continue
    last = [t, kind, t, txt]; out.append(last)
count = {}
for t0, kind, t1, txt in out:
    count[kind] = count.get(kind, 0) + 1
    print(f"  {t0:7.3f}{'-' + format(t1, '.3f') if t1 > t0 else '':8s}  {kind:9s} {txt}")
print("summary:", ", ".join(f"{k}: {v}" for k, v in count.items()) or "no warnings")
