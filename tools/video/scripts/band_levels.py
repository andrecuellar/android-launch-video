"""RMS per beat (dBFS) of the mid band (300-3000 Hz) and of the full signal.
The default phase (0.13036 s) and the beat period are example values from a past production (scripts/grid.py).
Usage: band_levels.py <audio> <from> <to> [phase] [gain_db]"""
import subprocess, sys
import numpy as np
from scipy.signal import butter, sosfiltfilt
SR = 48000
path, a0, z0 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
F0 = float(sys.argv[4]) if len(sys.argv) > 4 else 0.13036
g = 10 ** ((float(sys.argv[5]) if len(sys.argv) > 5 else 0.0) / 20)
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(raw, dtype=np.float32).astype(np.float64) * g
m = sosfiltfilt(butter(4, [300, 3000], btype="band", fs=SR, output="sos"), x)
P = 0.49999948887468326
db = lambda v: 20 * np.log10(np.sqrt(np.mean(v ** 2)) + 1e-12)
k = int(np.ceil((a0 - F0) / P - 1e-3)); row = []
while F0 + k * P < z0 - 1e-6:
    a = F0 + k * P; i, j = int(a * SR), int((a + P) * SR); row.append((a, db(m[i:j]), db(x[i:j]))); k += 1
print("beat       mid band / full (dBFS), beats 1 to 4")
for i in range(0, len(row), 4):
    gg = row[i:i + 4]; print(f"{gg[0][0]:7.2f}  " + "   ".join(f"{b:6.1f}/{c:6.1f}" for _, b, c in gg))
