"""Jumps at the segment edges of a joined MP4: compares the step that crosses each edge with its neighbors.
Usage: venv/bin/python -I edges.py <video.mp4> [edges in frames...]
The default edges are the ones of final2.sh (example values from a past production: adapt them)."""
import subprocess, sys
import numpy as np
path = sys.argv[1]
edges = [int(x) for x in sys.argv[2:]] or [240, 480, 720, 960, 1200, 1440, 1680, 1920, 2100, 2280]
w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip().split(","))
wanted = sorted({b + d for b in edges for d in (-2, -1, 0, 1)})
expr = "+".join(f"eq(n\\,{n})" for n in wanted)
p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", f"select='{expr}'", "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
F = {}
for n in wanted:
    buf = p.stdout.read(w * h * 3); F[n] = np.frombuffer(buf, dtype=np.uint8).astype(np.int16)
p.wait()
d = lambda a, b: float(np.abs(F[b] - F[a]).mean())
for b in edges:
    before, cross, after = d(b - 2, b - 1), d(b - 1, b), d(b, b + 1)
    near = max(before, after)
    mark = "  <- check" if cross > max(1.0, 2.5 * near) else ""
    print(f"  edge {b} ({b / 60:.2f} s): previous step {before:.3f}, cross {cross:.3f}, next step {after:.3f}{mark}")
