"""Shape of what sounds in the mid band (300-3000 Hz) on every beat, to tell hits shaped like a voice (gliding
harmonics: diagonal stripes) from synth notes (horizontal stripes) and drums (vertical stripes). Glide index = mean
of Gt*Gf / mean of (Gt²+Gf²) over the spectrogram in dB (log frequency axis, in semitones), only on the strong
pixels: > 0 stripes going down, < 0 stripes going up, ~0 horizontal or vertical. Also: |index| without sign (glide
in any direction) and the mid band ratio.
The default phase (0.13036 s) and the beat period are example values from a past production: pass the phase of your
track (scripts/grid.py).
Usage: hit_shape.py <audio> <from> <to> [phase]"""
import subprocess, sys
import numpy as np
from scipy.signal import stft
from scipy.ndimage import gaussian_filter
SR = 48000
path, a0, z0 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
F0 = float(sys.argv[4]) if len(sys.argv) > 4 else 0.13036
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
i0, i1 = int(max(0, a0 - 1) * SR), int((z0 + 1) * SR)
f, t, Z = stft(x[i0:i1], SR, nperseg=4096, noverlap=4096 - 240)
t = t + i0 / SR
# log axis: 1/6 of a semitone between 300 and 3000 Hz
st = np.arange(0, 12 * np.log2(3000 / 300), 1 / 6)
fq = 300 * 2 ** (st / 12)
M = np.abs(Z)
L = np.array([np.interp(fq, f, M[:, j]) for j in range(M.shape[1])]).T
L = 20 * np.log10(L + 1e-9)
L = gaussian_filter(L, (2, 1.5))
Gf, Gt = np.gradient(L)  # Gf along rows (frequency), Gt along columns (time)
P = 0.49999948887468326
k = int(np.ceil((a0 - F0) / P - 1e-3)); row = []
while F0 + k * P < z0 - 1e-6:
    a = F0 + k * P
    sel = (t >= a - 0.02) & (t < a + P - 0.02)
    Ls, gt, gf = L[:, sel], Gt[:, sel], Gf[:, sel]
    strong = Ls > np.percentile(Ls, 70)
    num = (gt * gf)[strong].mean(); den = (gt ** 2 + gf ** 2)[strong].mean() + 1e-9
    ab = np.abs(gt * gf)[strong].mean() / den
    row.append((a, num / den, ab))
    k += 1
print("beat       glide index (signed / unsigned), per beat 1 to 4")
for i in range(0, len(row), 4):
    g = row[i:i + 4]
    print(f"{g[0][0]:7.2f}  " + "   ".join(f"{s:+.3f}/{u:.3f}" for _, s, u in g))
