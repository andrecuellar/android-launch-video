"""Beat grid of a track: exact tempo, kick phase and energy per bar.

Usage: python grid.py track.mp3 > grid.json
"""
import json
import subprocess
import sys

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt

SR = 44100


def read(path):
    raw = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def main():
    x = read(sys.argv[1])
    # Kick band: 40 to 120 Hz, envelope with a 10 ms window.
    sos = butter(4, [40, 120], btype="band", fs=SR, output="sos")
    b = sosfiltfilt(sos, x)
    env = np.sqrt(np.convolve(b * b, np.ones(441) / 441, mode="same"))
    step = 44  # 1 ms
    e = env[::step]
    fps = SR / step
    # Kick peaks: at least 0.35 s apart and with relative prominence.
    peaks, _ = find_peaks(e, distance=int(0.35 * fps), prominence=np.percentile(e, 75) * 0.5)
    t_peaks = peaks / fps
    # Tempo from the median of the intervals close to one beat.
    d = np.diff(t_peaks)
    d = d[(d > 0.4) & (d < 0.6)]
    period = float(np.median(d))
    # Linear fit: beat index against time, with the peaks that fall on the grid.
    k = np.round((t_peaks - t_peaks[0]) / period)
    for _ in range(3):
        A = np.vstack([k, np.ones_like(k)]).T
        (p, f0), *_ = np.linalg.lstsq(A, t_peaks, rcond=None)
        res = t_peaks - (k * p + f0)
        good = np.abs(res) < 0.03
        k, t_peaks = k[good], t_peaks[good]
        period = p
    phase = float(f0 % period)
    # Energy per 4-beat bar (RMS in dB), to find rises, breaks and endings.
    total = len(x) / SR
    bars = []
    t = phase
    while t + 4 * period <= total:
        a, z = int(t * SR), int((t + 4 * period) * SR)
        rms = float(np.sqrt(np.mean(x[a:z] ** 2)) + 1e-12)
        rb = float(np.sqrt(np.mean(b[a:z] ** 2)) + 1e-12)
        bars.append({"start": round(t, 4), "db": round(20 * np.log10(rms), 1), "kick_db": round(20 * np.log10(rb), 1)})
        t += 4 * period
    json.dump({
        "bpm": round(60 / period, 3),
        "period": period,
        "first_beat_phase": phase,
        "peaks_used": int(len(t_peaks)),
        "duration": total,
        "bars": bars,
    }, sys.stdout, indent=1)


main()
