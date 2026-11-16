"""F1 and F2 trajectory (LPC) and energy over a stretch of a voice, to check whether a word (e.g. the brand name)
starts with the expected open vowel (high F1) or with /i/ (low F1, high F2).
Usage: formants.py <voice.wav> <from> <to>"""
import subprocess, sys
import numpy as np
from scipy.signal import lfilter
SR = 10000
path, a, z = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
c = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(c, dtype=np.float32).astype(np.float64)
x = lfilter([1, -0.63], [1], x)
def lpc(seg, p=10):
    r = np.correlate(seg, seg, "full")[len(seg) - 1:len(seg) + p]
    A = np.zeros(p + 1); A[0] = 1; e = r[0] + 1e-9
    for i in range(1, p + 1):
        k = -(r[i] + np.dot(A[1:i], r[i - 1:0:-1])) / e
        A[1:i + 1] = A[1:i + 1] + k * np.concatenate([A[1:i][::-1], [1]])
        e *= 1 - k * k
    return A
N, H = int(0.025 * SR), int(0.010 * SR)
for t in np.arange(a, z, 0.01):
    i = int(t * SR); seg = x[i:i + N] * np.hamming(N)
    db = 10 * np.log10(np.mean(seg ** 2) + 1e-12)
    if db < -45: print(f"{t:6.2f}  {db:6.1f} dB  (silence / stop consonant)"); continue
    roots = np.roots(lpc(seg)); roots = roots[np.imag(roots) > 0]
    f = np.angle(roots) * SR / (2 * np.pi); bw = -np.log(np.abs(roots)) * SR / np.pi
    fs = sorted(fr for fr, b in zip(f, bw) if fr > 200 and b < 500)
    print(f"{t:6.2f}  {db:6.1f} dB  F1 {fs[0] if fs else 0:6.0f}  F2 {fs[1] if len(fs) > 1 else 0:6.0f}")
