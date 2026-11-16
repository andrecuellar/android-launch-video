"""Where the voice is not the loudest thing: 400 ms windows with voice, voice against music and against effects separately.
Run it from the folder that holds placed-voice.wav, the stems folder stems-16x9/ (music-only.wav, sfx-rest.wav,
sfx-final.wav) and the report of narrated_mix.py, mix-report-16x9.json. The 0.2 to 40.8 s range covers a 41 s film;
example value: set it to your film.
Usage: venv/bin/python -I check_margin.py"""
import os, sys, json, importlib.util
import numpy as np
spec = importlib.util.spec_from_file_location("mz", os.path.join(os.path.dirname(os.path.abspath(__file__)), "narrated_mix.py")); mz = importlib.util.module_from_spec(spec); spec.loader.exec_module(mz)
SR = mz.SR
voice = mz.read("placed-voice.wav"); mus = mz.read("stems-16x9/music-only.wav"); fx = mz.read("stems-16x9/sfx-rest.wav"); ff = mz.read("stems-16x9/sfx-final.wav")
rep = json.load(open("mix-report-16x9.json"))
g_fx = 10 ** (rep["sfx_gain_db"] / 20)
n = min(map(len, (voice, mus, fx, ff))); voice, mus, fx, ff = voice[:n], mus[:n], fx[:n], ff[:n]
# rebuild the music ducking from the report (same rule as the mix)
t = np.arange(n) / SR; duck = np.zeros(n)
for d in rep["sentences"]:
    a, z, dd = d["from"], d["to"], d["duck_db"]; at = 0.0 if a >= mz.CLOSING else mz.ATTACK
    r = np.zeros(n); r[max(0, int((a - at) * SR)):int(z * SR)] = dd
    if at: k0 = int((a - at) * SR); r[k0:int(a * SR)] = dd * np.clip((t[k0:int(a * SR)] - (a - at)) / at, 0, 1)
    i1, i2 = int(z * SR), min(n, int((z + mz.DUCK_RELEASE) * SR)); r[i1:i2] = np.maximum(r[i1:i2], dd * (1 - (t[i1:i2] - z) / mz.DUCK_RELEASE))
    duck = np.maximum(duck, r)
w = int(0.02 * SR); duck = np.convolve(duck, np.ones(w) / w, mode="same")
musd = mus * 10 ** (-duck / 20)[:, None]
vk, mk, fk, ffk = (mz.k_weight(x) for x in (voice, musd, fx * g_fx, ff))
H = int(0.01 * SR); env = np.sqrt(np.convolve(voice[:, 0] ** 2, np.ones(H) / H, mode="same")); active = env > np.abs(voice).max() * 10 ** (-40 / 20)
bad = []
for c in np.arange(0.2, 40.8, 0.1):
    if active[int((c - 0.2) * SR):int((c + 0.2) * SR)].mean() < 0.8: continue
    lv = mz.loudness(vk, c - .2, c + .2); lm = mz.loudness(mk, c - .2, c + .2); lf = mz.loudness(fk, c - .2, c + .2); lff = mz.loudness(ffk, c - .2, c + .2)
    rest = 10 * np.log10(10 ** (lm / 10) + 10 ** (lf / 10) + 10 ** (lff / 10))
    if lv - rest < 0: bad.append((round(c, 2), round(lv, 1), round(lm, 1), round(lf, 1), round(lff, 1)))
print("windows with the voice under the rest (t, voice, music, effects, final effects):")
for m in bad: print("  ", m)
