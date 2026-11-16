"""Film soundtrack: track montage, sound effects synthesized on the beat and a mix at -14 LUFS.

Usage: venv/bin/python -I audio.py <track.mp3> <cues.json> <out_dir> [duration]
Writes: music.wav, sfx.wav, mix.wav (48 kHz, 24 bit), measurement.txt, sfx-peaks.json.
Every effect is placed so that ITS measured peak lands on the film time the film exports.
cues.json is the list exported by the film (snap.mjs ... --cues): [{"t", "type", ...}], see synthesize().
"""
import json
import os
import subprocess
import sys

import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt

SR = 48000
TRACK, CUES_PATH, OUT_DIR = sys.argv[1], sys.argv[2], sys.argv[3]
DUR = float(sys.argv[4]) if len(sys.argv) > 4 else 33.0
os.makedirs(OUT_DIR, exist_ok=True)

# All track times, sections and treatments below are example values from a past production: adapt them to the
# chosen track. Measure its grid first (scripts/grid.py) and check the result with scripts/fingerprint.py and
# scripts/music_check.py.
# Measured grid (scripts/grid.py): 120.0001 BPM, phase 0.13036 s; the kick peak lands 2.6 ms before the line.
# Track montage (every section starts on a bar line). Bars that carry an unwanted layer (for example a chopped vocal
# layer, "hits shaped like a voice") are left out.
SECTIONS = [  # (film from, track from, treatment)
    (0.0, 12.1303, None),     # film 0 to 18 -> track 12.13 to 30.13 (drop at film 4.0 = track 16.13)
    (18.0, 78.1303, None),    # film 18 to 20 -> track 78.13 to 80.13: bar 8 of a phrase, without the unwanted hit
    (20.0, 32.1303, "echo"),  # film 20 to 28 -> track 32.13 to 40.13; its start carries the echo of the previous hit
    (28.0, 24.1303, None),    # film 28 to 34 -> track 24.13 to 30.13: bars 5 to 7 of the first drop phrase
    (34.0, 78.1303, None),    # film 34 to 36 -> track 78.13 to 80.13: clean bar 8 before the hit
    (36.0, 96.1303, "tail"),  # film 36 -> track 96.13: final hit and tail; the tail carries the echo of the hit before it
]
# Every splice: a 14 ms equal power crossfade that ends 10 ms before the kick peak of the incoming section
# (-27 to -13 ms from the line), in the dip of the outgoing section: the incoming kick plays whole and covers the splice.
CROSSFADE = (-0.027, -0.013)
# "echo": from track 32.09 to 33.10 (the first two beats of 32.13), in 120 ms windows every 40 ms, every third of an
# octave from 300 to 3200 Hz is brought to the level of the same window in the reference bars (which carry no echo):
# it only goes down, never up; the gain is smoothed in time and applied in the STFT.
ECHO = {"from": 32.09, "to": 33.10, "window": 0.12, "step": 0.04, "refs": (34.1303, 36.1303), "band": (300.0, 3200.0), "margin_db": 1.0}
# "tail": the 170 to 3500 Hz band drops 22 dB before the hit (the last ms of the previous hit that fall in the
# crossfade) and after its attack (the echo); the attack of the hit (track 96.115 to 96.15) stays whole in every band.
TAIL = {"band": (170.0, 3500.0), "gain_db": -22.0, "attack": (96.105, 96.115, 96.15, 96.175)}

# C# minor pentatonic (C#, E, F#, G#, B), measured from the bass of the track (C#2 and E2). Example: use the key of
# your track (scripts/key_detect.py, scripts/bass.py).
PENTA = [554.37, 659.26, 739.99, 830.61, 987.77, 1108.73, 1318.51, 1479.98]


def read(path, channels=2):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", str(channels), "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, channels).astype(np.float64)


def write(path, x, bits=24):
    x = np.clip(x, -1, 1)
    proc = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f64le", "-ar", str(SR), "-ac", "2", "-i", "-",
                           "-c:a", "pcm_s24le" if bits == 24 else "pcm_f32le", path], input=x.astype(np.float64).tobytes(), check=True)
    return proc


def measure(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    out = {}
    lines = r.splitlines()
    for i, l in enumerate(lines):
        l = l.strip()
        if l.startswith("I:"): out["integrated_lufs"] = float(l.split()[1])
        elif l.startswith("LRA:"): out["lra_lu"] = float(l.split()[1])
        elif l.startswith("Peak:"): out["true_peak_dbtp"] = float(l.split()[1])
    return out


# ---------------- Music ----------------
track = read(TRACK)
n = int(DUR * SR)
t = np.arange(n) / SR
THIRDS = 1000 * 2 ** (np.arange(-17, 11) / 3)


def thirds_db(x, a, z):
    seg = x[int(a * SR):int(z * SR)].mean(axis=1)
    e = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    f = np.fft.rfftfreq(len(seg), 1 / SR)
    return np.array([10 * np.log10(e[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].sum() + 1e-20) for c in THIRDS])


def treat_echo(x):
    """Lowers the echo of the previous hit at the start of the section: third octave equalization, window by window,
    against the neighbor bars (only down, never up), applied in the STFT domain with a gain smoothed in time."""
    from scipy.signal import stft, istft
    from scipy.ndimage import uniform_filter1d
    in_band = (THIRDS >= ECHO["band"][0]) & (THIRDS <= ECHO["band"][1])
    centers = np.arange(ECHO["from"], ECHO["to"] - ECHO["window"] + 1e-9, ECHO["step"]) + ECHO["window"] / 2
    cuts = []
    for c in centers:
        a = c - ECHO["window"] / 2
        ref = np.mean([thirds_db(x, r + (a - 32.1303), r + (a - 32.1303) + ECHO["window"]) for r in ECHO["refs"]], axis=0)
        excess = thirds_db(x, a, a + ECHO["window"]) - ref
        cuts.append(np.where(in_band, -np.clip(excess - ECHO["margin_db"], 0, 24), 0.0))
    cuts = np.array(cuts)  # (windows, thirds)
    a0, z0 = int((ECHO["from"] - 0.4) * SR), int((ECHO["to"] + 0.4) * SR)
    nps, hop = 2048, 256
    out = x.copy()
    for ch in range(x.shape[1]):
        f, tt, Z = stft(x[a0:z0, ch], SR, window="hann", nperseg=nps, noverlap=nps - hop)
        tt = tt + a0 / SR
        # gain in dB per (third, frame): interpolated between windows, 0 outside, smoothed in time (about 60 ms)
        gdb_t = np.array([np.interp(tt, np.concatenate([[ECHO["from"] - 0.03], centers, [ECHO["to"] + 0.03]]),
                                    np.concatenate([[0.0], cuts[:, k], [0.0]]), left=0, right=0) for k in range(len(THIRDS))])
        gdb_t = uniform_filter1d(gdb_t, size=max(1, int(0.06 * SR / hop)), axis=1)
        logf = np.log(np.maximum(f, 1))
        G = np.array([10 ** (np.interp(logf, np.log(THIRDS), gdb_t[:, j], left=0, right=0) / 20) for j in range(len(tt))]).T
        _, y = istft(Z * G, SR, window="hann", nperseg=nps, noverlap=nps - hop)
        out[a0:z0, ch] = y[:z0 - a0]
    return out, {"windows": len(centers), "max_cut_db": round(float(cuts.min()), 1),
                 "mean_cut_db_per_third": [round(float(v), 1) for v in cuts.mean(axis=0)]}


def treat_tail(x):
    lo, hi = TAIL["band"]
    lows = sosfiltfilt(butter(4, lo, btype="low", fs=SR, output="sos"), x, axis=0)
    highs = sosfiltfilt(butter(4, hi, btype="high", fs=SR, output="sos"), x, axis=0)
    mid = x - lows - highs  # what is left between the two (the sum of the three parts is the exact signal)
    tt = np.arange(len(x)) / SR
    a0, a1, b0, b1 = TAIL["attack"]
    opens = np.clip((tt - a0) / (a1 - a0), 0, 1); closes = np.clip((tt - b0) / (b1 - b0), 0, 1)
    whole = (0.5 - 0.5 * np.cos(np.pi * opens)) * (0.5 + 0.5 * np.cos(np.pi * closes))  # 1 during the attack, 0 outside
    g = 10 ** (TAIL["gain_db"] / 20)
    gain = g + (1 - g) * whole
    return x + (gain[:, None] - 1) * mid


sources = {None: track}
echo_report = None
for _, _, treat in SECTIONS:
    if treat == "echo" and "echo" not in sources:
        sources["echo"], echo_report = treat_echo(track)
    elif treat == "tail" and "tail" not in sources:
        sources["tail"] = treat_tail(track)


def segment(source, film0, track0):
    idx = np.round((track0 - film0 + t) * SR).astype(int)
    ok = (idx >= 0) & (idx < len(source))
    y = np.zeros((n, 2))
    y[ok] = source[idx[ok]]
    return y


music = np.zeros((n, 2))
for i, (f0, t0, treat) in enumerate(SECTIONS):
    w = np.ones(n)
    if i > 0:  # comes in with a sine in the crossfade of its line
        u = np.clip((t - (f0 + CROSSFADE[0])) / (CROSSFADE[1] - CROSSFADE[0]), 0, 1)
        w *= np.sin(u * np.pi / 2)
    if i + 1 < len(SECTIONS):  # goes out with a cosine in the crossfade of the next section
        f1 = SECTIONS[i + 1][0]
        u = np.clip((t - (f1 + CROSSFADE[0])) / (CROSSFADE[1] - CROSSFADE[0]), 0, 1)
        w *= np.cos(u * np.pi / 2)
    if w.max() > 0:
        music += segment(sources[treat], f0, t0) * w[:, None]
music[: int(0.010 * SR)] *= np.linspace(0, 1, int(0.010 * SR))[:, None]  # no click at the start
# Tail: the example track ends in silence after its last section; nothing else to do.

# ---------------- Synthesis ----------------
rng_global = np.random.default_rng(7)


def noise(m, seed):
    return np.random.default_rng(seed).standard_normal(m)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype="low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype="high", fs=SR, output="sos"), x)


def sine_glide(f, durs):
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def env_ad(m, attack, decay):
    tt = np.arange(m) / SR
    e = np.exp(-np.maximum(0, tt - attack) / decay)
    if attack > 0:
        e *= np.clip(tt / attack, 0, 1)
    return e


def sfx_tap(seed):
    m = int(0.07 * SR); tt = np.arange(m) / SR
    f = 900 + 600 * np.exp(-tt / 0.012)
    body = sine_glide(f, m) * env_ad(m, 0.0006, 0.011)
    click = bp(noise(m, seed), 2500, 7500) * env_ad(m, 0.0002, 0.0025)
    thump = np.sin(2 * np.pi * 170 * tt) * env_ad(m, 0.001, 0.016)
    return 0.55 * body + 0.5 * click / (np.abs(click).max() + 1e-9) + 0.45 * thump


def sfx_release(seed):
    m = int(0.04 * SR); tt = np.arange(m) / SR
    f = 1700 + 700 * np.exp(-tt / 0.006)
    return 0.6 * sine_glide(f, m) * env_ad(m, 0.0004, 0.006) + 0.3 * bp(noise(m, seed), 3500, 9000) * env_ad(m, 0.0002, 0.0015)


def sfx_pop(note, seed):
    f0 = PENTA[note % len(PENTA)]
    m = int(0.28 * SR); tt = np.arange(m) / SR
    f = f0 * (1 + 0.45 * np.exp(-tt / 0.010))
    tone = sine_glide(f, m) * env_ad(m, 0.002, 0.085) + 0.22 * sine_glide(2 * f, m) * env_ad(m, 0.002, 0.04)
    breath = bp(noise(m, seed), 1200, 5000) * env_ad(m, 0.001, 0.006)
    return tone + 0.18 * breath / (np.abs(breath).max() + 1e-9)


def sfx_tick(note, seed):
    f0 = PENTA[(note + 3) % len(PENTA)] * 2
    m = int(0.09 * SR)
    return 0.7 * sine_glide(np.full(m, f0), m) * env_ad(m, 0.0008, 0.022) + 0.35 * bp(noise(m, seed), 3000, 9000) * env_ad(m, 0.0002, 0.002)


def sfx_odometer_tick(note, seed):
    m = int(0.025 * SR); tt = np.arange(m) / SR
    click = bp(noise(m, seed), 2600, 7000, 2) * env_ad(m, 0.0001, 0.0013)
    reso = np.sin(2 * np.pi * (3100 + 160 * (note % 4)) * tt) * env_ad(m, 0.0002, 0.0035)
    return click / (np.abs(click).max() + 1e-9) * 0.7 + 0.35 * reso


def sfx_stretch(down, seed):
    m = int(0.2 * SR); tt = np.arange(m) / SR
    f = 280 + 300 * (tt / 0.2) if not down else 580 - 300 * (tt / 0.2)
    tone = sine_glide(f, m) * np.sin(np.pi * np.clip(tt / 0.2, 0, 1)) ** 1.5
    rub = bp(noise(m, seed), 900, 3200) * np.sin(np.pi * np.clip(tt / 0.2, 0, 1)) ** 2
    return 0.7 * tone + 0.25 * rub / (np.abs(rub).max() + 1e-9)


def sfx_sweep(dur, up, seed, weights=(1, 1, 1, 1, 1)):
    m = int((dur + 0.15) * SR); tt = np.arange(m) / SR
    base = noise(m, seed)
    bands = [(250, 600), (500, 1200), (1000, 2400), (2000, 4800), (4000, 9000)]
    x = np.zeros(m)
    for i, (lo, hi) in enumerate(bands):
        frac = i / (len(bands) - 1)
        center = (frac if up else (0.25 + 0.5 * np.sin(np.pi * frac))) * dur
        e = np.exp(-((tt - center - 0.05) / (0.32 * dur)) ** 2)
        y = bp(base, lo, hi)
        x += weights[i] * e * y / (np.abs(y).max() + 1e-9)
    total = np.sin(np.pi * np.clip(tt / (dur + 0.12), 0, 1)) ** 1.2
    return x * total


def sfx_riser(dur, seed):
    """Layer of the reinforcement of the sweep that reaches the final hit: noise in a band that rises from 180 to
    700 Hz and grows up to the hit. It is noise (no gliding harmonics, no formants) and stays under 1 kHz: no voice
    and no brightness."""
    m = int(dur * SR); tt = np.arange(m) / SR
    base = noise(m, seed)
    centers = 180 * (700 / 180) ** (np.arange(8) / 7)
    x = np.zeros(m)
    for i, fc in enumerate(centers):
        y = bp(base, fc / 2 ** 0.35, fc * 2 ** 0.35)
        e = np.exp(-((tt - (0.15 + 0.85 * i / 7) * dur) / (0.22 * dur)) ** 2)
        x += e * y / (np.abs(y).max() + 1e-9)
    grows = np.clip(tt / dur, 0, 1) ** 2.2
    closing = np.clip((dur - tt) / 0.006, 0, 1)  # the last 6 ms go down to zero (no click) right before the hit
    return x * grows * (0.5 - 0.5 * np.cos(np.pi * closing))


def sfx_hit(strength, final, seed):
    length = 1.8 if final else 0.5
    m = int(length * SR); tt = np.arange(m) / SR
    f = 42 + 58 * np.exp(-tt / 0.06)
    sub = sine_glide(f, m) * env_ad(m, 0.001, 0.32 if final else 0.18)
    crack = lp(noise(m, seed), 2400) * env_ad(m, 0.0005, 0.018)
    body = np.sin(2 * np.pi * 150 * tt) * env_ad(m, 0.001, 0.05)
    x = 0.9 * sub + 0.45 * crack / (np.abs(crack).max() + 1e-9) + 0.3 * body
    if final:  # very soft tonal tail in C# minor (C#3, G#3, C#4, E4)
        chord = sum(np.sin(2 * np.pi * fr * tt) * (0.5 if fr < 200 else 0.3) for fr in (138.59, 207.65, 277.18, 329.63))
        x += 0.12 * chord * env_ad(m, 0.004, 0.55)
        tail = bp(noise(m, seed + 1), 300, 5000) * env_ad(m, 0.002, 0.45)
        x += 0.05 * tail / (np.abs(tail).max() + 1e-9)
    return x * strength


def sfx_word(note, seed):
    f0 = PENTA[note % len(PENTA)]
    m = int(0.6 * SR)
    return sine_glide(np.full(m, f0), m) * env_ad(m, 0.003, 0.22) + 0.18 * sine_glide(np.full(m, 3 * f0), m) * env_ad(m, 0.002, 0.07)


def sfx_compress(seed):
    m = int(0.42 * SR); tt = np.arange(m) / SR
    f = 120 + 330 * np.exp(-tt / 0.12)
    tone = sine_glide(f, m) * np.sin(np.pi * np.clip(tt / 0.42, 0, 1)) ** 1.5
    air = lp(noise(m, seed), 1800) * np.sin(np.pi * np.clip(tt / 0.42, 0, 1)) ** 2
    return 0.7 * tone + 0.3 * air / (np.abs(air).max() + 1e-9)


def sfx_headline(seed):
    m = int(0.16 * SR); tt = np.arange(m) / SR
    s = bp(noise(m, seed), 3500, 10000) * np.sin(np.pi * np.clip(tt / 0.16, 0, 1)) ** 2
    return s / (np.abs(s).max() + 1e-9)


def sfx_badge(seed):
    m = int(0.9 * SR); tt = np.arange(m) / SR
    f0 = PENTA[5]
    bell = sum(a * np.sin(2 * np.pi * f0 * k * tt) * env_ad(m, 0.001, d) for k, a, d in ((1, 1.0, 0.45), (2.76, 0.4, 0.2), (5.4, 0.18, 0.08)))
    return bell


def sfx_confirm(seed):  # a progress track completes: two rising notes (G#5 and C#6)
    m = int(0.5 * SR); tt = np.arange(m) / SR
    n1 = sine_glide(np.full(m, PENTA[3]), m) * env_ad(m, 0.002, 0.09)
    d = int(0.07 * SR)
    n2 = np.zeros(m); n2[d:] = (sine_glide(np.full(m - d, PENTA[5]), m - d) * env_ad(m - d, 0.002, 0.18))
    return 0.8 * n1 + n2 + 0.15 * sine_glide(np.full(m, 2 * PENTA[5]), m) * env_ad(m, 0.002, 0.05)


def sfx_notification(seed):  # system notification: two soft bell notes (E6 and B5)
    m = int(0.9 * SR); tt = np.arange(m) / SR
    def bell(f, d0):
        x = np.zeros(m); i = int(d0 * SR)
        x[i:] = sum(a * np.sin(2 * np.pi * f * k * tt[: m - i]) * env_ad(m - i, 0.001, dd) for k, a, dd in ((1, 1.0, 0.35), (2.0, 0.25, 0.12), (3.01, 0.1, 0.06)))
        return x
    return bell(PENTA[6], 0.0) + 0.85 * bell(PENTA[4], 0.11)


def sfx_drag(dur, seed):
    m = int((dur + 0.1) * SR); tt = np.arange(m) / SR
    e = np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 0.8 * (0.75 + 0.25 * np.sin(2 * np.pi * 17 * tt))
    s = bp(noise(m, seed), 1100, 3800) * e
    return s / (np.abs(s).max() + 1e-9)


# peak level of every effect before the bus (dBFS)
LEVEL = {"notification": -10, "underline": -16, "confirm": -10, "tap": -9, "release": -17, "pop": -9, "tick": -15, "odometer_tick": -21, "stretch": -15, "sweep": -13,
         "hit": -3, "word": -15, "compress": -15, "headline": -27, "badge": -12, "drag": -22}
PEAK_DELAY = {"badge": 0.2}  # the bell sounds when the stroke finishes drawing
# Reinforcement of the sweep that reaches the final hit: more body in the lows and low mids, the voice mids the same
# and fewer highs; plus a low noise riser that ends right before the hit.
REINFORCE = {"window": 0.45, "weights": (2.0, 0.9, 0.8, 0.85, 0.6), "level": -10.5, "riser_dur": 0.62, "riser_level": -16.0, "riser_before": 0.004}


def synthesize(c, seed):
    """Cue types and their optional fields (all from window.CUES of the film):
    tap; release; pop {note, strength}; tick {note}; odometer_tick {note}; stretch {down, soft};
    sweep {dur, up, strength}; hit {strength, final}; word {note}; compress; headline; badge; drag {dur};
    confirm; notification; underline. Unknown types are skipped."""
    k = c["type"]
    if k == "tap": return sfx_tap(seed)
    if k == "release": return sfx_release(seed)
    if k == "pop": return sfx_pop(int(c.get("note", 0)), seed) * float(c.get("strength", 1))
    if k == "tick": return sfx_tick(int(c.get("note", 0)), seed)
    if k == "odometer_tick": return sfx_odometer_tick(int(c.get("note", 0)), seed)
    if k == "stretch": return sfx_stretch(bool(c.get("down", 0)), seed) * (0.6 if c.get("soft") else 1.0)
    if k == "sweep": return sfx_sweep(float(c.get("dur", 0.4)), bool(c.get("up", 0)), seed) * float(c.get("strength", 1))
    if k == "hit": return sfx_hit(float(c.get("strength", 1)), bool(c.get("final", 0)), seed)
    if k == "word": return sfx_word(int(c.get("note", 0)), seed)
    if k == "compress": return sfx_compress(seed)
    if k == "headline": return sfx_headline(seed)
    if k == "badge": return sfx_badge(seed)
    if k == "drag": return sfx_drag(float(c.get("dur", 1)), seed)
    if k == "confirm": return sfx_confirm(seed)
    if k == "notification": return sfx_notification(seed)
    if k == "underline": return sfx_stretch(False, seed) * 0.5
    return None


cues = json.load(open(CUES_PATH))
sfx = np.zeros(n)
sfx_final = np.zeros(n)  # the reinforced sweep, its riser and the final hit (for the narrated version)
log = []
T_FINAL = next((c["t"] for c in cues if c["type"] == "hit" and c.get("final")), None)
reinforced = []
for i, c in enumerate(sorted(cues, key=lambda x: x["t"])):
    reinforce = c["type"] == "sweep" and T_FINAL is not None and 0 < T_FINAL - c["t"] <= REINFORCE["window"]
    if reinforce:
        s = sfx_sweep(float(c.get("dur", 0.4)), bool(c.get("up", 0)), 1000 + i, weights=REINFORCE["weights"])
        level = REINFORCE["level"]
    else:
        s = synthesize(c, 1000 + i)
        level = LEVEL.get(c["type"], 0)
    if s is None:
        continue
    peak_abs = np.abs(s).max() + 1e-12
    s = s / peak_abs * 10 ** (level / 20)
    env = np.convolve(np.abs(s), np.ones(int(0.001 * SR)) / int(0.001 * SR), mode="same")
    ip = int(np.argmax(env))  # measured peak of the effect itself
    target = c["t"] + PEAK_DELAY.get(c["type"], 0.0)
    start = int(round(target * SR)) - ip
    a0, b0 = max(0, start), min(n, start + len(s))
    if b0 > a0:
        sfx[a0:b0] += s[a0 - start:b0 - start]
        if reinforce or (c["type"] == "hit" and c.get("final")):
            sfx_final[a0:b0] += s[a0 - start:b0 - start]
    log.append({"t": c["t"], "type": c["type"], "peak_at": round((start + ip) / SR, 4), "level_dbfs": level})
    if reinforce:
        reinforced.append(c["t"])
if reinforced:  # the riser ends right before the final hit (not aligned by its peak: it runs up to the hit)
    s = sfx_riser(REINFORCE["riser_dur"], 4242)
    s = s / (np.abs(s).max() + 1e-12) * 10 ** (REINFORCE["riser_level"] / 20)
    end = int(round((T_FINAL - REINFORCE["riser_before"]) * SR))
    start = end - len(s)
    sfx[max(0, start):end] += s[max(0, -start):]
    sfx_final[max(0, start):end] += s[max(0, -start):]
    log.append({"t": round(T_FINAL - REINFORCE["riser_before"], 4), "type": "riser (sweep reinforcement)", "from": round(start / SR, 4), "level_dbfs": REINFORCE["riser_level"]})

# ---------------- Very soft closing pad (C# minor) ----------------
pad = np.zeros(n)
t0c, t1c = 37.2, DUR  # example start time from a past production: adapt it to the end card of your film
mask = (t >= t0c) & (t < t1c)
tc = t[mask] - t0c
chord = np.zeros(mask.sum())
for fr, a_ in ((138.59, 0.55), (164.81, 0.35), (207.65, 0.45), (277.18, 0.3), (329.63, 0.18)):
    for det in (-0.12, 0.12):
        chord += a_ * np.sin(2 * np.pi * (fr + det) * tc + 1.3 * fr)
chord = lp(chord, 1400)
env_c = np.clip(tc / 1.2, 0, 1) ** 2 * np.clip((t1c - t0c - tc) / 1.6, 0, 1) ** 1.5
pad[mask] = chord / (np.abs(chord).max() + 1e-9) * env_c * 10 ** (-30 / 20)

# ---------------- Mix ----------------
mono_sfx = sfx * 0.62 + pad
mix = music * 0.5 + mono_sfx[:, None]
write(os.path.join(OUT_DIR, "music.wav"), music * 0.5)
write(os.path.join(OUT_DIR, "sfx.wav"), np.stack([mono_sfx, mono_sfx], axis=1))
if os.environ.get("AUDIO_STEMS"):  # separate stems for the narrated version (they do not change this mix)
    rest = (sfx - sfx_final) * 0.62
    final_ = sfx_final * 0.62 + pad
    write(os.path.join(OUT_DIR, "sfx-rest.wav"), np.stack([rest, rest], axis=1), bits=32)
    write(os.path.join(OUT_DIR, "sfx-final.wav"), np.stack([final_, final_], axis=1), bits=32)
    write(os.path.join(OUT_DIR, "music-only.wav"), music * 0.5, bits=32)
raw_mix = os.path.join(OUT_DIR, "mix-raw.wav")
write(raw_mix, mix, bits=32)
m0 = measure(raw_mix)
gain_db = -14.0 - m0["integrated_lufs"]
mix2 = mix * 10 ** (gain_db / 20)
pre = os.path.join(OUT_DIR, "mix-pre.wav")
write(pre, mix2, bits=32)
m1 = measure(pre)
final = os.path.join(OUT_DIR, "mix.wav")
limiter = m1["true_peak_dbtp"] > -1.5  # headroom for AAC
if limiter:  # true peak limiter, without makeup gain
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", pre, "-af",
                    "aresample=192000,alimiter=limit=0.78:attack=1:release=60:level=disabled,aresample=48000",
                    "-c:a", "pcm_s24le", final], check=True)
else:
    write(final, mix2)
m2 = measure(final)

# ---------------- Splice evidence (it cannot be heard here: it is measured) ----------------
def bands_db(x, a, z):
    seg = x[int(a * SR):int(z * SR)].mean(axis=1)
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    f = np.fft.rfftfreq(len(seg), 1 / SR)
    out = []
    for lo, hi in ((20, 120), (120, 500), (500, 2000), (2000, 6000), (6000, 16000)):
        out.append(round(10 * np.log10(spec[(f >= lo) & (f < hi)].sum() + 1e-12), 1))
    return out


rms = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


def clicks(i):
    """Splice of section i: the assembled music against the louder of the two unfaded sections (the outgoing one,
    continued, and the incoming one, as if it were already playing), in 1 ms windows from T-35 to T+15 ms: energy
    above 6 kHz and maximum second difference. A click would show a clear excess over both sections; 0 dB and 1.00
    means there is none."""
    T = SECTIONS[i][0]
    A = segment(sources[SECTIONS[i - 1][2]], SECTIONS[i - 1][0], SECTIONS[i - 1][1]).mean(axis=1)
    B = segment(sources[SECTIONS[i][2]], SECTIONS[i][0], SECTIONS[i][1]).mean(axis=1)
    M = music.mean(axis=1)
    a, z = int((T - 0.06) * SR), int((T + 0.04) * SR)
    sos = butter(4, 6000, btype="high", fs=SR, output="sos")
    ha, hb, hm = (sosfiltfilt(sos, v[a:z]) for v in (A, B, M))
    w = int(0.001 * SR)
    excess = max(10 * np.log10((np.mean(hm[k:k + w] ** 2) + 1e-14) / (max(np.mean(ha[k:k + w] ** 2), np.mean(hb[k:k + w] ** 2)) + 1e-14))
                 for k in range(int(0.025 * SR), int(0.075 * SR), w))
    d2 = lambda v: np.abs(np.diff(v[a:z][int(0.025 * SR):int(0.075 * SR)], 2)).max()
    return excess, d2(M) / max(d2(A), d2(B))


with open(os.path.join(OUT_DIR, "measurement.txt"), "w") as fo:
    fo.write("Soundtrack: measurement (not listened to; numbers only)\n")
    fo.write(f"duration {DUR:.2f} s, 48 kHz stereo\n")
    fo.write("montage (film -> track): " + "; ".join(f"{f0:g} -> {t0:.2f}" + (f" ({tr})" if tr else "") for f0, t0, tr in SECTIONS) + "\n")
    fo.write(f"equal power crossfades of {(CROSSFADE[1] - CROSSFADE[0]) * 1000:.0f} ms, from {CROSSFADE[0] * 1000:+.0f} to {CROSSFADE[1] * 1000:+.0f} ms of every line\n")
    if echo_report:
        fo.write(f"echo ({ECHO['from']}-{ECHO['to']}): {echo_report['windows']} windows; max cut {echo_report['max_cut_db']} dB; "
                 f"mean cut per third of an octave {echo_report['mean_cut_db_per_third']}\n")
    fo.write(f"tail: band {TAIL['band'][0]:.0f}-{TAIL['band'][1]:.0f} Hz at {TAIL['gain_db']:+.0f} dB\n")
    fo.write(f"reinforced sweep at {reinforced}; riser up to {T_FINAL}\n")
    fo.write(f"raw mix: {m0}\n")
    fo.write(f"applied gain: {gain_db:+.2f} dB; before the limiter: {m1}\n")
    fo.write(f"true peak limiter: {'yes' if limiter else 'no'}\n")
    fo.write(f"FINAL (mix.wav): {m2}\n")
    for i in range(1, len(SECTIONS)):
        f0 = SECTIONS[i][0]
        ex, d2 = clicks(i)
        fo.write(f"splice {f0:g} s: energy above 6 kHz {ex:+.1f} dB and second difference {d2:.2f} times the louder of the two unfaded sections; "
                 f"bands (20-120, 120-500, 500-2k, 2k-6k, 6k-16k Hz, dB) 150 ms before {[float(v) for v in bands_db(music, f0 - 0.18, f0 - 0.03)]} / after {[float(v) for v in bands_db(music, f0, f0 + 0.15)]}\n")
json.dump(log, open(os.path.join(OUT_DIR, "sfx-peaks.json"), "w"), indent=1, ensure_ascii=False)
print(open(os.path.join(OUT_DIR, "measurement.txt")).read())
