"""Track grid measured again: period, phase, kick peaks at every splice and key.

The splice targets and the key sections (16.13-32.13 and 88.13-96.13 s) are example values from a past production:
set them to the bar lines your montage uses (SECTIONS in audio.py).

Usage: venv/bin/python -I grid.py track.mp3 out.json
"""
import json
import subprocess
import sys

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt

SR = 48000


def read(path, channels=1):
    raw = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", path, "-ac", str(channels), "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, check=True,
    ).stdout
    x = np.frombuffer(raw, dtype=np.float32).copy()
    return x.reshape(-1, channels) if channels > 1 else x


def kick_envelope(x):
    sos = butter(4, [40, 120], btype="band", fs=SR, output="sos")
    b = sosfiltfilt(sos, x)
    window = int(0.006 * SR)
    env = np.sqrt(np.convolve(b * b, np.ones(window) / window, mode="same"))
    return b, env


def fit_grid(env):
    step = SR // 1000  # 1 ms
    e = env[::step]
    fps = 1000.0
    peaks, _ = find_peaks(e, distance=int(0.35 * fps), prominence=np.percentile(e, 75) * 0.5)
    t = peaks / fps
    d = np.diff(t)
    d = d[(d > 0.45) & (d < 0.55)]
    period = float(np.median(d))
    k = np.round((t - t[0]) / period)
    for _ in range(4):
        A = np.vstack([k, np.ones_like(k)]).T
        (p, f0), *_ = np.linalg.lstsq(A, t, rcond=None)
        res = t - (k * p + f0)
        good = np.abs(res) < 0.02
        k, t = k[good], t[good]
        period = float(p)
    res = t - (k * period + f0)
    return period, float(f0 % period), len(t), float(np.std(res) * 1000), float(np.max(np.abs(res)) * 1000)


def local_peak(env, t_approx, radius=0.06):
    a, z = int((t_approx - radius) * SR), int((t_approx + radius) * SR)
    seg = env[a:z]
    i = int(np.argmax(seg))
    t_peak = (a + i) / SR
    v = seg[i]
    # Onset: last crossing of 20 % of the peak before the peak.
    j = i
    while j > 0 and seg[j] > 0.2 * v:
        j -= 1
    return round(t_peak, 4), round((a + j) / SR, 4), round(20 * np.log10(v + 1e-12), 1)


def key(x, start, end):
    seg = x[int(start * SR):int(end * SR)]
    n = 16384
    hop = 4096
    window = np.hanning(n)
    chroma = np.zeros(12)
    freq = np.fft.rfftfreq(n, 1 / SR)
    valid = (freq > 60) & (freq < 2000)
    note = np.round(12 * np.log2(freq[valid] / 440.0)).astype(int) % 12  # 0 = A
    for i in range(0, len(seg) - n, hop):
        m = np.abs(np.fft.rfft(seg[i:i + n] * window))[valid] ** 2
        np.add.at(chroma, note, m)
    chroma = np.roll(chroma, -3)  # 0 = C
    chroma /= chroma.max()
    major = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    candidates = []
    for r in range(12):
        candidates.append((float(np.corrcoef(chroma, np.roll(major, r))[0, 1]), names[r] + " major", r, "major"))
        candidates.append((float(np.corrcoef(chroma, np.roll(minor, r))[0, 1]), names[r] + " minor", r, "minor"))
    candidates.sort(reverse=True)
    return [round(float(c), 3) for c in chroma], candidates[:4]


def main():
    path, out = sys.argv[1], sys.argv[2]
    x = read(path)
    b, env = kick_envelope(x)
    period, phase, used, std_ms, max_ms = fit_grid(env)
    targets = [12.13, 14.13, 16.13, 18.13, 30.13, 31.63, 32.13, 32.63, 86.13, 87.63, 88.13, 88.63, 94.13, 95.63, 96.13, 96.63]
    peaks = {}
    for t in targets:
        k = round((t - phase) / period)
        t_grid = k * period + phase
        tp, ta, db = local_peak(env, t_grid)
        peaks[f"{t:.2f}"] = {"grid": round(t_grid, 4), "peak": tp, "onset": ta, "db": db,
                             "offset_ms": round((tp - t_grid) * 1000, 1)}
    chroma, keys = key(x, 16.13, 32.13)
    chroma2, keys2 = key(x, 88.13, 96.13)
    json.dump({
        "bpm": round(60 / period, 4),
        "period": period,
        "phase": phase,
        "peaks_used": used,
        "residual_std_ms": round(std_ms, 2),
        "residual_max_ms": round(max_ms, 2),
        "peaks": peaks,
        "chroma_drop": chroma,
        "key_drop": keys,
        "key_ending": keys2,
    }, open(out, "w"), indent=1, ensure_ascii=False)
    print(open(out).read())


main()
