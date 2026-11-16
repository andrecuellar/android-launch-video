"""Spectrogram (40 Hz to 8 kHz, log axis) of a stretch of audio with bar lines (cyan) and beat lines (gray),
and the 300 and 3000 Hz lines (green). The default phase (0.13036 s) and the beat period are example values from a
past production (scripts/grid.py).
Usage: track_spectrum.py <audio> <from> <to> <out.png> [phase]"""
import subprocess, sys
import numpy as np
from scipy.signal import stft
SR = 48000
path, a, z, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
F0 = float(sys.argv[5]) if len(sys.argv) > 5 else 0.13036
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(raw, dtype=np.float32).astype(np.float64)[int(a*SR):int(z*SR)]
f, t, Z = stft(x, SR, nperseg=2048, noverlap=2048-240)
S = 20*np.log10(np.abs(Z)+1e-9)
W, H = 2400, 640
fy = np.exp(np.linspace(np.log(8000), np.log(40), H))
fi = np.clip(np.searchsorted(f, fy), 0, len(f)-1)
ti = np.clip((np.arange(W) / W * len(t)).astype(int), 0, len(t)-1)
img = S[fi][:, ti]
v = np.clip((img - (img.max() - 70)) / 70, 0, 1)
rgb = np.stack([np.clip(v*1.6, 0, 1), np.clip(v*1.6-0.5, 0, 1)**0.8, np.clip(0.35*v + (v > 0.85)*(v-0.85)*4, 0, 1)], axis=-1)
rgb = (rgb*255).astype(np.uint8)
for fr in (300, 3000):
    yy = int(np.argmin(np.abs(fy - fr))); rgb[yy, ::4] = (60, 255, 60)
P = 0.49999948887468326
k = int(np.ceil((a - F0)/P)); labels = []
while F0 + k*P < z:
    tl = F0 + k*P; xx = int((tl - a) / (z - a) * W)
    if 0 <= xx < W:
        if k % 4 == 0: rgb[:, xx] = (0, 255, 255); labels.append((xx, tl))
        else: rgb[::3, xx] = (200, 200, 200)
    k += 1
raw_path = out + ".rgb"
open(raw_path, "wb").write(rgb.tobytes())
txt = ",".join(f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='{tl:.2f}':x={xx+4}:y=6:fontsize=18:fontcolor=cyan" for xx, tl in labels)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-i", raw_path, "-vf", txt or "null", "-frames:v", "1", out], check=True)
import os; os.remove(raw_path)
