"""Tempo, beat regularity and energy arc of each track, to pick the music.

Usage: python analyze.py mp3/*.mp3 > analysis.json
(download the tracks of list.txt into mp3/ first; Mixkit license: https://mixkit.co/license/)
"""
import json
import subprocess
import sys

import numpy as np

SR = 22050
HOP = 512


def read(path):
    raw = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32)


def envelope(x):
    n = 2048
    window = np.hanning(n).astype(np.float32)
    frames = 1 + (len(x) - n) // HOP
    idx = np.arange(n)[None, :] + HOP * np.arange(frames)[:, None]
    spectrum = np.abs(np.fft.rfft(x[idx] * window, axis=1))
    spectrum = np.log1p(spectrum * 10)
    flux = np.maximum(0, np.diff(spectrum, axis=0)).sum(axis=1)
    flux = flux - np.convolve(flux, np.ones(16) / 16, mode="same")
    lows = spectrum[:, 1:12]  # about 10 to 120 Hz: the kick
    low_flux = np.maximum(0, np.diff(lows, axis=0)).sum(axis=1)
    return np.maximum(flux, 0), low_flux


def tempo(flux):
    fps = SR / HOP
    f = flux - flux.mean()
    ac = np.correlate(f, f, mode="full")[len(f) - 1:]
    ac /= ac[0] + 1e-9
    best = []
    for bpm in np.arange(90, 150.25, 0.25):
        lag = 60 * fps / bpm
        l0 = int(np.floor(lag))
        v = ac[l0] * (1 - (lag - l0)) + ac[l0 + 1] * (lag - l0)
        # also twice the period, to reward a stable beat
        lag2 = 2 * lag
        l2 = int(np.floor(lag2))
        v2 = ac[l2] * (1 - (lag2 - l2)) + ac[l2 + 1] * (lag2 - l2)
        best.append((v + 0.5 * v2, bpm))
    score, bpm = max(best)
    return float(bpm), float(score)


def energy(x):
    seg = SR
    n = len(x) // seg
    rms = np.sqrt((x[: n * seg].reshape(n, seg) ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms)


def main():
    output = []
    for path in sys.argv[1:]:
        try:
            x = read(path)
        except subprocess.CalledProcessError:
            continue
        flux, lows = envelope(x)
        bpm, regularity = tempo(flux)
        db = energy(x)
        smooth = np.convolve(db, np.ones(4) / 4, mode="same")
        # The biggest energy rise in 4 s: a "drop" candidate.
        jump = smooth[4:] - smooth[:-4]
        i = int(np.argmax(jump)) if len(jump) else 0
        output.append({
            "file": path,
            "bpm": round(bpm, 2),
            "regularity": round(regularity, 3),
            "duration": len(x) / SR,
            "median_db": round(float(np.median(db)), 1),
            "db_range": round(float(np.percentile(db, 95) - np.percentile(db, 10)), 1),
            "drop_s": i + 4,
            "drop_jump_db": round(float(jump[i]) if len(jump) else 0, 1),
            "kick_strength": round(float(np.percentile(lows, 90) / (np.median(lows) + 1e-9)), 2),
        })
    json.dump(output, sys.stdout, indent=1)


main()
