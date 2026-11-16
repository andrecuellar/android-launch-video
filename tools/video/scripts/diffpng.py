"""Difference between two images: the box that contains it and its magnitude. Usage: diffpng.py a.png b.png"""
import subprocess, sys
import numpy as np
def read(r):
    info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", r], capture_output=True, text=True).stdout.strip().split(",")
    w, h = int(info[0]), int(info[1])
    b = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", r, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(b, dtype=np.uint8).reshape(h, w, 3).astype(np.int16)
a, b = read(sys.argv[1]), read(sys.argv[2])
d = np.abs(a - b).max(axis=2)
ys, xs = np.nonzero(d > 8)
if len(ys) == 0: print(f"max {d.max()} (no visible differences)"); sys.exit()
print(f"max {d.max()}, pixels >8: {len(ys)}, box x {xs.min()}-{xs.max()} y {ys.min()}-{ys.max()}")
