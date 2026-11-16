"""Chroma (12 pitch classes, 80-2000 Hz) per half bar and similarity of a reference bar with the others.
The reference bar (94.13), the bars listed and the beat period are example values from a past production: set them
from your track (scripts/grid.py).
Usage: chroma_bars.py <audio>"""
import subprocess, sys
import numpy as np
from scipy.signal import stft
SR = 48000
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", sys.argv[1], "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
f, t, Z = stft(x, SR, nperseg=8192, noverlap=8192 - 960)
M = np.abs(Z) ** 2
sel = (f >= 80) & (f <= 2000)
pc = (np.round(12 * np.log2(f[sel] / 440.0)) + 9) % 12  # 0 = C
C = np.zeros((12, len(t)))
for k in range(12): C[k] = M[sel][pc == k].sum(axis=0)
names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
def chroma(a, z):
    v = C[:, (t >= a) & (t < z)].sum(axis=1); return v / (np.linalg.norm(v) + 1e-12)
P = 0.49999948887468326
bars = [round(72.13 + 2 * i, 2) for i in range(12)]
print("bar      1st half (3 strongest notes)       2nd half")
for b in bars:
    a1, a2 = chroma(b, b + 2 * P), chroma(b + 2 * P, b + 4 * P)
    top = lambda v: " ".join(names[i] for i in np.argsort(-v)[:3])
    print(f"{b:6.2f}   {top(a1):28s}   {top(a2)}")
ref = np.concatenate([chroma(94.13, 94.13 + 2 * P), chroma(94.13 + 2 * P, 94.13 + 4 * P)])
print("similarity (cosine) of bar 94.13 with every bar:")
for b in bars:
    v = np.concatenate([chroma(b, b + 2 * P), chroma(b + 2 * P, b + 4 * P)])
    print(f"  {b:6.2f}  {np.dot(ref, v) / 2:.3f}")
