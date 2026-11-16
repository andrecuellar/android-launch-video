"""Ratio of 300-3000 Hz energy per beat (mean of STFT frames of 1024 samples, left and right channels averaged).
The default phase (0.13036 s) and the beat period are example values from a past production (scripts/grid.py).
Usage: midband_beats.py <audio> <from> <to> [phase]"""
import subprocess, sys
import numpy as np
from scipy.signal import stft
SR = 48000
path, a0, z0 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
F0 = float(sys.argv[4]) if len(sys.argv) > 4 else 0.13036
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
X = np.frombuffer(raw, dtype=np.float32).astype(np.float64).reshape(-1, 2)
P = 0.49999948887468326
def ratios(x):
    f, t, Z = stft(x, SR, nperseg=1024, noverlap=768)
    E = np.abs(Z) ** 2
    return t, E[(f >= 300) & (f < 3000)].sum(axis=0) / (E[(f >= 20) & (f < 20000)].sum(axis=0) + 1e-12)
tL, rL = ratios(X[:, 0]); _, rR = ratios(X[:, 1]); r = (rL + rR) / 2
k = int(np.ceil((a0 - F0) / P - 1e-3)); row = []
while F0 + k * P < z0 - 1e-6:
    a = F0 + k * P; row.append((a, float(r[(tL >= a) & (tL < a + P)].mean()))); k += 1
for i in range(0, len(row), 4):
    g = row[i:i + 4]; print(f"{g[0][0]:7.2f}  " + "  ".join(f"{v:.2f}" for _, v in g))
