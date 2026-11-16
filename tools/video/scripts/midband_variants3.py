"""Tries variants of the mid band ratio (300-3000 Hz) per beat (STFT size, mono or left, aggregate, offset) and
ranks them by how well they reproduce target values on known unwanted beats, next to the range on clean bars.
The targets (bar, beat): ratio and the clean bars are example values from a past production: set them from your track.
Usage: midband_variants3.py <audio>"""
import subprocess, sys, itertools
import numpy as np
from scipy.signal import stft
SR = 48000
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", sys.argv[1], "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
X = np.frombuffer(raw, dtype=np.float32).astype(np.float64).reshape(-1, 2)
P = 0.49999948887468326
def line(bar, beat): return bar + (beat - 1) * P
target = {(94.13, 2): 0.29, (94.13, 3): 0.33, (94.13, 4): 0.38, (92.13, 3): 0.33}
clean = [(b, p) for b in np.arange(72.13, 86.14, 2.0) for p in (1, 2, 3, 4)]
for nps, mono, agg, off in itertools.product((512, 1024, 2048, 4096), (True, False), ("mean", "median", "max", "p75"), (0.0, -0.02)):
    x = X.mean(axis=1) if mono else X[:, 0]
    f, t, Z = stft(x, SR, nperseg=nps, noverlap=nps - nps // 4)
    E = np.abs(Z) ** 2
    r = E[(f >= 300) & (f < 3000)].sum(axis=0) / (E[(f >= 20) & (f < 20000)].sum(axis=0) + 1e-12)
    def val(a, z):
        sel = r[(t >= a) & (t < z)]
        return {"mean": np.mean, "median": np.median, "max": np.max, "p75": lambda v: np.percentile(v, 75)}[agg](sel)
    v = {k: val(line(*k) + off, line(*k) + off + P) for k in target}
    lv = [val(line(b, p) + off, line(b, p) + off + P) for b, p in clean]
    err = sum((v[k] - target[k]) ** 2 for k in target)
    print(f"err {err:.4f} nps {nps} mono {mono!s:5s} {agg:7s} off {off:5.2f}: " + " ".join(f"{q:.2f}" for q in v.values()) + f" | clean {min(lv):.2f}-{max(lv):.2f} (p10-p90 {np.percentile(lv,10):.2f}-{np.percentile(lv,90):.2f})")
