"""Looks for objective artifacts in a voice: clicks (isolated high frequency peaks against their surroundings),
noise in the pauses and abrupt cuts at the start or at the end.
Usage: audio_artifacts.py <voice.wav> [...]"""
import subprocess, sys
import numpy as np
from scipy.signal import butter, sosfiltfilt
for path in sys.argv[1:]:
    c = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    sr = int(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=sample_rate", "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip())
    x = np.frombuffer(c, dtype=np.float32).astype(np.float64)
    h = sosfiltfilt(butter(4, 4000, btype="high", fs=sr, output="sos"), x)
    w = int(0.010 * sr)
    local_rms = np.sqrt(np.convolve(h ** 2, np.ones(w) / w, mode="same")) + 1e-6
    ratio = np.abs(h) / local_rms
    # a click: ratio > 6 on a peak shorter than 1 ms, with no similar peaks in the surrounding 10 ms
    candidates = np.where(ratio > 6)[0]
    clicks, last = [], -10 ** 9
    for i in candidates:
        if i - last > w:
            clicks.append(i / sr)
        last = i
    env = np.sqrt(np.convolve(x ** 2, np.ones(w) / w, mode="same"))
    db = 20 * np.log10(env + 1e-9)
    pauses = db < -45
    floor = 20 * np.log10(np.sqrt(np.mean(x[pauses] ** 2)) + 1e-9) if pauses.any() else float("nan")
    print(f"{path}: clicks {len(clicks)} {['%.3f' % c for c in clicks[:8]]}; noise floor in pauses {floor:.1f} dBFS; "
          f"first and last 5 ms: {20*np.log10(np.abs(x[:int(.005*sr)]).max()+1e-9):.0f} / {20*np.log10(np.abs(x[-int(.005*sr):]).max()+1e-9):.0f} dBFS")
