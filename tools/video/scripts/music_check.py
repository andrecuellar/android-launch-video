"""Checks of the film music (it is not listened to here: it is measured).
Usage: venv/bin/python -I music_check.py <track.mp3> <new music.wav> [previous music.wav]
1. Fingerprint of the unwanted hits (scripts/fingerprint.py) on every beat and half beat from 0 to 36 s (and from 36 to 41, apart).
2. Glide index (stripes going down in 300-3000 Hz) per beat.
3. Clicks at the splices: the assembled music against the two unfaded sections, in 1 ms windows from T-35 to T+15 ms.
The time ranges (36 and 41 s) and the thresholds are example values from a past production: adapt them to your film.
"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fingerprint import Fingerprint, read_mono, P, SR
from scipy.signal import stft, butter, sosfiltfilt
from scipy.ndimage import gaussian_filter

track_path, new_path = sys.argv[1], sys.argv[2]
previous_path = sys.argv[3] if len(sys.argv) > 3 else None
track = read_mono(track_path)
H = Fingerprint(track)
new = read_mono(new_path)
previous = read_mono(previous_path) if previous_path else None

# 1. fingerprint
grid = np.round(np.arange(0, 36.0, 0.25), 2)
vals = [(g, H.similarity(new, g)) for g in grid]
print("1. Fingerprint on beats and half beats, film 0 to 36 s (new music). The 10 highest:")
for g, v in sorted(vals, key=lambda r: -r[1])[:10]:
    extra = f"   (before {H.similarity(previous, g):.2f})" if previous is not None else ""
    print(f"   {g:6.2f} s   {v:.3f}{extra}")
mx = max(v for _, v in vals)
print(f"   max {mx:.3f}; beats and half beats >= 0.88: {sum(v >= 0.88 for _, v in vals)} of {len(vals)}")
if previous is not None:
    va = [(g, H.similarity(previous, g)) for g in grid]
    print("   before (previous music): >= 0.88 at " + ", ".join(f"{g:.2f} ({v:.2f})" for g, v in va if v >= 0.88))
tail = [(g, H.similarity(new, g)) for g in np.round(np.arange(36.0, 41.0, 0.25), 2)]
print("   apart, 36 to 41 s (final hit and tail): max " + f"{max(v for _, v in tail):.3f}; " + " ".join(f"{g:.2f}:{v:.2f}" for g, v in tail[:12]))
if previous is not None:
    print("   before, 36 to 39 s: " + " ".join(f"{g:.2f}:{H.similarity(previous, g):.2f}" for g, _ in tail[:12]))

# 2. glide index
def glide(x, a0, z0):
    i0, i1 = int(max(0, a0 - 1) * SR), int(min(len(x) / SR, z0 + 1) * SR)
    f, t, Z = stft(x[i0:i1], SR, nperseg=4096, noverlap=4096 - 240)
    t = t + i0 / SR
    st = np.arange(0, 12 * np.log2(3000 / 300), 1 / 6); fq = 300 * 2 ** (st / 12)
    M = np.abs(Z); L = np.array([np.interp(fq, f, M[:, j]) for j in range(M.shape[1])]).T
    L = gaussian_filter(20 * np.log10(L + 1e-9), (2, 1.5)); Gf, Gt = np.gradient(L)
    out = []
    for k in range(int(round(a0 / P)), int(round(z0 / P))):
        a = k * P; sel = (t >= a - 0.02) & (t < a + P - 0.02)
        Ls, gt, gf = L[:, sel], Gt[:, sel], Gf[:, sel]; strong = Ls > np.percentile(Ls, 70)
        out.append((a, (gt * gf)[strong].mean() / ((gt ** 2 + gf ** 2)[strong].mean() + 1e-9)))
    return out
d = glide(new, 0.0, 41.0)
print("2. Glide index per beat (voice shaped hits of the example track: +0.05 to +0.12; rest of the track: -0.02 to +0.04):")
print(f"   new music, 0 to 41 s: max {max(v for _, v in d):+.3f} at {max(d, key=lambda r: r[1])[0]:.2f} s; beats > +0.045: " + (", ".join(f"{a:.2f} ({v:+.3f})" for a, v in d if v > 0.045) or "none"))
if previous is not None:
    da = glide(previous, 0.0, 41.0)
    print("   previous music: beats > +0.045: " + ", ".join(f"{a:.2f} ({v:+.3f})" for a, v in da if v > 0.045))

# 3. clicks at the splices: the music is assembled with the same code as audio.py and compared with the unfaded sections
code = open(os.path.join(HERE, "audio.py")).read().split("# ---------------- Synthesis ----------------")[0]
namespace = {"__name__": "montage"}
argv0 = sys.argv
sys.argv = ["audio.py", track_path, "-", os.path.join(HERE, "..", "new-audio", "tmp-montage"), "41.0"]
exec(compile(code, "audio.py (montage)", "exec"), namespace)
sys.argv = argv0
mus, segment, sources, SEC, XF = namespace["music"], namespace["segment"], namespace["sources"], namespace["SECTIONS"], namespace["CROSSFADE"]
hp = butter(4, 6000, btype="high", fs=SR, output="sos")
print("3. Clicks at the splices (1 ms windows from T-35 to T+15 ms; the assembled music against the louder of the two unfaded sections):")
for i in range(1, len(SEC)):
    T = SEC[i][0]
    A = segment(sources[SEC[i - 1][2]], SEC[i - 1][0], SEC[i - 1][1]).mean(axis=1)
    B = segment(sources[SEC[i][2]], SEC[i][0], SEC[i][1]).mean(axis=1)
    M = mus.mean(axis=1)
    a, z = int((T - 0.06) * SR), int((T + 0.04) * SR)
    ha, hb, hm = (sosfiltfilt(hp, v[a:z]) for v in (A, B, M))
    excess_hf, excess_d2 = -99.0, 0.0
    for k in range(int(0.025 * SR), int(0.075 * SR), int(0.001 * SR)):
        sl = slice(k, k + int(0.001 * SR))
        e = lambda v: np.mean(v[sl] ** 2) + 1e-14
        excess_hf = max(excess_hf, 10 * np.log10(e(hm) / max(e(ha), e(hb))))
    d2 = lambda v: np.abs(np.diff(v[a:z][int(0.025 * SR):int(0.075 * SR)], 2)).max()
    excess_d2 = d2(M) / max(d2(A), d2(B))
    print(f"   {T:5.1f} s: energy > 6 kHz, max excess {excess_hf:+.1f} dB; max second difference {excess_d2:.2f} times the larger of the two sections")
