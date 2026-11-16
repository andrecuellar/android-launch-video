"""Offset of the audio of an MP4 against its source mix: cross correlation of the decoded audio (with its edit list
applied) against the WAV, in three stretches with hits. The stretch start times (3.5, 16.0, 35.5 s) are example
values from a past production: pick moments of your film with clear hits.
Usage: audio_offset.py <video.mp4> <mix.wav>"""
import subprocess, sys
import numpy as np
SR = 48000
def read(r):
    c = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", r, "-map", "0:a:0", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(c, dtype=np.float32).astype(np.float64)
v, w = read(sys.argv[1]), read(sys.argv[2])
res = []
for a in (3.5, 16.0, 35.5):
    i0, L, M = int(a * SR), int(1.5 * SR), int(0.05 * SR)
    ref = w[i0:i0 + L]
    best = max(range(-M, M + 1), key=lambda k: float(np.dot(v[i0 + k:i0 + k + L], ref)))
    c = np.dot(v[i0 + best:i0 + best + L], ref) / (np.linalg.norm(v[i0 + best:i0 + best + L]) * np.linalg.norm(ref) + 1e-12)
    res.append((a, best, c))
print(f"audio samples: video {len(v)} ({len(v) / SR:.4f} s), mix {len(w)} ({len(w) / SR:.4f} s)")
for a, k, c in res:
    print(f"   stretch from {a:5.1f} s: offset {k:+d} samples ({k / SR * 1000:+.2f} ms), correlation {c:.4f}")
