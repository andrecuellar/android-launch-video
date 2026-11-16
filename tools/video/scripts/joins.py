"""Compares two MP4s frame by frame (the new render and the previous one) over a range of frames.
Usage: venv/bin/python -I joins.py <new.mp4> <previous.mp4> <from> <to>
Prints, per frame, the maximum and mean difference (0-255, in RGB at full resolution).
"""
import subprocess, sys
import numpy as np
new, old, a, b = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", new], capture_output=True, text=True).stdout.strip().split(","))
def frames(path):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", f"select='between(n\\,{a}\\,{b})'", "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    while True:
        buf = p.stdout.read(w * h * 3)
        if len(buf) < w * h * 3: break
        yield np.frombuffer(buf, dtype=np.uint8).astype(np.int16)
    p.wait()
equal = 0; rows = []
for i, (x, y) in enumerate(zip(frames(new), frames(old))):
    d = np.abs(x - y); mx, md = int(d.max()), float(d.mean())
    rows.append((a + i, mx, md)); equal += mx == 0
for n, mx, md in rows:
    if b - a <= 12 or mx > 0: print(f"  frame {n} ({n / 60:.3f} s): max diff {mx}, mean {md:.4f}")
print(f"{len(rows)} frames compared; identical: {equal}")
