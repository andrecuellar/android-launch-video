"""Smoothness only in fast motion: the span between the first and the last frame that changes a
lot (YAVG > STRONG) of each scroll; inside it, intervals between frames that change somewhat.

Usage: python3 measure_quick.py <video> [y0:y1]   (default 288:2064 for a 1080x2400 clip)"""
import re, subprocess, sys, statistics
v = sys.argv[1]; zone = sys.argv[2] if len(sys.argv) > 2 else "288:2064"
y0, y1 = map(int, zone.split(":"))
s = subprocess.run(["ffmpeg", "-v", "error", "-i", v, "-vf", f"crop=iw:{y1-y0}:0:{y0},tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-", "-f", "null", "-"], capture_output=True, text=True).stdout
t = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", s)]; y = [float(x) for x in re.findall(r"YAVG=([0-9.]+)", s)]
STRONG, SOME, CUT = 1.5, 0.25, 0.3
strong = [a for a, b in zip(t, y) if b > STRONG]
groups, g = [], []
for a in strong:
    if g and a - g[-1] > CUT: groups.append(g); g = []
    g.append(a)
if g: groups.append(g)
total = []
for i, g in enumerate([g for g in groups if len(g) >= 8], 1):
    start, end = g[0], g[-1]
    changes = [a for a, b in zip(t, y) if start <= a <= end and b > SOME]
    ints = [b - a for a, b in zip(changes, changes[1:])]
    total += ints
    print(f"  motion {i}: {start:.2f}-{end:.2f} s, {len(changes)} frames, {(len(changes)-1)/(end-start):.1f} fps, max {max(ints)*1000:.0f} ms, >20 ms: {sum(x>0.020 for x in ints)}, >35 ms: {sum(x>0.035 for x in ints)}")
if total:
    print(f"  TOTAL: {1/statistics.mean(total):.1f} fps, max {max(total)*1000:.0f} ms, >20 ms: {sum(x>0.020 for x in total)} of {len(total)}, >35 ms: {sum(x>0.035 for x in total)}")
