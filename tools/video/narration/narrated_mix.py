"""Mix of the narrated version of a format: voice + music with sidechain ducking + sound effects.

- The voice leads. Under every sentence the music goes down until it sits 10.5 dB under the voice (target range
  9 to 12), measured with K weighting sentence by sentence; 120 ms attack with lookahead (the music is already down
  when the voice comes in) and 400 ms release; pauses shorter than 0.35 s do not let it come back up (no pumping).
- The effects sit 3 dB under the voice (median of the momentary loudness of every effect against the voice).
- The final hit, its sweep and the logo: the music stays up (it does not go down from the hit until the closing voice
  comes in) and those effects play with the music, as in the mix without voice; under the closing voice the music
  goes down 6 dB at most.
- Fixed gain to -14 LUFS and a true peak limiter (no makeup gain).

Inputs: the stems written by audio.py with AUDIO_STEMS=1 (music-only.wav, sfx-rest.wav, sfx-final.wav in the stems
folder) and its sfx-peaks.json.
Usage: venv/bin/python -I narrated_mix.py <voice.wav> <stems folder> <sfx-peaks.json> <out.wav> <report.json>
"""
import json
import subprocess
import sys

import numpy as np
from scipy.signal import lfilter

SR = 48000
MUSIC_TARGET_DB = 10.5
SFX_TARGET_DB = 3.0
ATTACK, DUCK_RELEASE, GAP = 0.12, 0.40, 0.35
CLOSING = 35.85         # from here on the music stays up (final hit and logo); example value: set it to your film
CLOSING_MAX_DUCK = 6.0  # under the closing voice, at most
HIT_TIME = 36.0         # time of the final hit, only for the report; example value: set it to your film


def read(path):
    c = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "2", "-ar", str(SR), "-f", "f64le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(c, dtype=np.float64).reshape(-1, 2).copy()


def write(path, x, bits=24):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f64le", "-ar", str(SR), "-ac", "2", "-i", "-", "-c:a",
                    "pcm_s24le" if bits == 24 else "pcm_f32le", path], input=np.clip(x, -1, 1).tobytes(), check=True)


def k_weight(x):
    """BS.1770 K filter at 48 kHz (shelf + high pass)."""
    y = lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585], x, axis=0)
    return lfilter([1.0, -2.0, 1.0], [1, -1.99004745483398, 0.99007225036621], y, axis=0)


def loudness(xk, a, z):
    s = xk[int(max(0.0, a) * SR):int(z * SR)]
    return -0.691 + 10 * np.log10(np.sum(np.mean(s ** 2, axis=0)) + 1e-20)


def measure(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    out = {}
    for l in r.splitlines():
        l = l.strip()
        if l.startswith("I:"): out["integrated_lufs"] = float(l.split()[1])
        elif l.startswith("LRA:"): out["lra_lu"] = float(l.split()[1])
        elif l.startswith("Peak:"): out["true_peak_dbtp"] = float(l.split()[1])
    return out


def main():
    voice_path, stems, peaks_path, out, report_path = sys.argv[1:6]
    voice = read(voice_path)
    music = read(f"{stems}/music-only.wav")
    fx = read(f"{stems}/sfx-rest.wav")
    fx_final = read(f"{stems}/sfx-final.wav")
    n = min(len(voice), len(music), len(fx), len(fx_final))
    voice, music, fx, fx_final = voice[:n], music[:n], fx[:n], fx_final[:n]
    t = np.arange(n) / SR

    # voice sentences: spans with voice (10 ms, threshold 40 dB under the peak), joining short pauses
    H = int(0.01 * SR)
    env = np.sqrt(np.convolve(voice[:, 0] ** 2, np.ones(H) / H, mode="same"))
    active = env > np.abs(voice).max() * 10 ** (-40 / 20)
    edges = np.flatnonzero(np.diff(np.concatenate([[0], active.astype(int), [0]])))
    spans = [[edges[i] / SR, edges[i + 1] / SR] for i in range(0, len(edges), 2)]
    joined = []
    for a, z in spans:
        if joined and a - joined[-1][1] < GAP: joined[-1][1] = z
        else: joined.append([a, z])
    sentences = [(a, z) for a, z in joined if z - a > 0.15]

    vk, mk, fk = k_weight(voice), k_weight(music), k_weight(fx)
    # music ducking per sentence, to sit MUSIC_TARGET_DB under the voice
    duck = np.zeros(n)
    detail = []
    for a, z in sentences:
        lv, lm = loudness(vk, a, z), loudness(mk, a, z)
        d = float(np.clip(lm - (lv - MUSIC_TARGET_DB), 0, 24))
        in_closing = a >= CLOSING
        if in_closing: d = min(d, CLOSING_MAX_DUCK)
        attack = 0.0 if in_closing else ATTACK  # in the closing the music does not go down before the voice: the hit stays whole
        r = np.zeros(n)
        i0, i1 = int((a - attack) * SR), int(z * SR)
        r[max(0, i0):i1] = d
        if attack > 0:
            k0 = max(0, i0); r[k0:int(a * SR)] = d * np.clip((t[k0:int(a * SR)] - (a - attack)) / attack, 0, 1)
        i2 = min(n, int((z + DUCK_RELEASE) * SR))
        r[i1:i2] = np.maximum(r[i1:i2], d * (1 - (t[i1:i2] - z) / DUCK_RELEASE))
        duck = np.maximum(duck, r)
        detail.append({"from": round(a, 3), "to": round(z, 3), "voice_lufs": round(lv, 1), "music_unducked_lufs": round(lm, 1), "duck_db": round(d, 1)})
    # no corners: 20 ms moving average over the dB
    w = int(0.02 * SR)
    duck = np.convolve(duck, np.ones(w) / w, mode="same")
    g_music = 10 ** (-duck / 20)

    # effects: 3 dB under the voice (median of the 400 ms momentary loudness of every effect against the voice)
    peaks = json.load(open(peaks_path))
    lv_mean = 10 * np.log10(np.mean([10 ** (loudness(vk, a, z) / 10) for a, z in sentences]))
    ev = []
    for p in peaks:
        tp = p.get("peak_at")
        if tp is None or tp >= CLOSING - 0.3: continue
        ev.append(loudness(fk, tp - 0.2, tp + 0.2))
    l_fx = float(np.median(ev))
    g_fx = 10 ** ((lv_mean - SFX_TARGET_DB - l_fx) / 20)

    # while the voice speaks, no effect goes above 3 dB under it: 400 ms loudness (every 10 ms) of the voice and of the
    # effects; where an effect goes over, it goes down just what is needed (the curve widens 100 ms and is smoothed 50 ms)
    def momentary(xk):
        e = np.sum(xk ** 2, axis=1)
        v = np.convolve(e, np.ones(int(0.4 * SR)) / int(0.4 * SR), mode="same")
        return -0.691 + 10 * np.log10(v + 1e-20)
    lv_t = momentary(vk)[::H]
    lf_t = momentary(fk * g_fx)[::H]
    act_t = np.convolve(active[::H].astype(float), np.ones(40) / 40, mode="same") >= 0.5
    excess = np.where(act_t, np.maximum(0, lf_t - (lv_t - SFX_TARGET_DB)), 0.0)
    from scipy.ndimage import maximum_filter1d, uniform_filter1d
    excess = uniform_filter1d(maximum_filter1d(excess, size=21), size=5)
    fx_cut = np.interp(t, np.arange(len(excess)) * H / SR, excess)
    g_fx_t = g_fx * 10 ** (-fx_cut / 20)
    mix = voice + music * g_music[:, None] + fx * g_fx_t[:, None] + fx_final
    raw = out.replace(".wav", "-raw.wav")
    write(raw, mix, bits=32)
    m0 = measure(raw)
    gain = 10 ** ((-14.0 - m0["integrated_lufs"]) / 20)
    pre = out.replace(".wav", "-pre.wav")
    write(pre, mix * gain, bits=32)
    m1 = measure(pre)
    if m1["true_peak_dbtp"] > -1.5:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", pre, "-af",
                        "aresample=192000,alimiter=limit=0.78:attack=1:release=60:level=disabled,aresample=48000", "-c:a", "pcm_s24le", out], check=True)
    else:
        write(out, mix * gain)
    m2 = measure(out)
    if abs(m2["integrated_lufs"] + 14.0) >= 0.05:  # the limiter ate some loudness: correct the gain once and limit again
        gain *= 10 ** ((-14.0 - m2["integrated_lufs"]) / 20)
        write(pre, mix * gain, bits=32)
        m1 = measure(pre)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", pre, "-af",
                        "aresample=192000,alimiter=limit=0.78:attack=1:release=60:level=disabled,aresample=48000", "-c:a", "pcm_s24le", out], check=True)
        m2 = measure(out)

    # check with the adjusted stems
    music_final, fx_adjusted = music * g_music[:, None], fx * g_fx_t[:, None]
    mfk, fak = k_weight(music_final), k_weight(fx_adjusted)
    for dd in detail:
        dd["music_under_voice_lufs"] = round(loudness(mfk, dd["from"], dd["to"]), 1)
        dd["voice_minus_music_db"] = round(dd["voice_lufs"] - dd["music_under_voice_lufs"], 1)
    ev2 = [loudness(fak, p["peak_at"] - 0.2, p["peak_at"] + 0.2) for p in peaks if p.get("peak_at") is not None and p["peak_at"] < CLOSING - 0.3]
    # is the voice the loudest thing? 400 ms windows every 100 ms inside the sentences: voice against everything else together
    rest_k = k_weight(music_final + fx_adjusted + fx_final)
    margins = []
    for a, z in sentences:
        for c in np.arange(a + 0.2, z - 0.2 + 1e-9, 0.1):
            if active[int((c - 0.2) * SR):int((c + 0.2) * SR)].mean() < 0.8:
                continue  # pause inside the group: nobody speaks there
            margins.append((round(float(c), 2), loudness(vk, c - 0.2, c + 0.2) - loudness(rest_k, c - 0.2, c + 0.2)))
    worst = min(margins, key=lambda m: m[1])
    report = {"voice_over_rest_min_db": round(worst[1], 1), "voice_over_rest_min_at": worst[0],
              "windows_with_voice_under": sum(1 for _, m in margins if m < 0), "windows_measured": len(margins),
              "voice_over_rest_median_db": round(float(np.median([m for _, m in margins])), 1),
              "sentences": detail, "voice_mean_lufs": round(lv_mean, 1), "sfx_median_lufs": round(float(np.median(ev2)), 1),
              "sfx_under_voice_db": round(lv_mean - float(np.median(ev2)), 1), "sfx_gain_db": round(20 * np.log10(g_fx), 1),
              "music_at_hit_db": round(float(-duck[int(HIT_TIME * SR)]), 1),
              "sfx_cut_under_voice_max_db": round(float(fx_cut.max()), 1),
              "sfx_cut_under_voice_s": round(float(np.sum(fx_cut > 0.5) / SR), 2), "raw": m0, "before_limiter": m1, "final": m2,
              "total_gain_db": round(20 * np.log10(gain), 2)}
    json.dump(report, open(report_path, "w"), indent=1, ensure_ascii=False)
    for dd in detail:
        print(f"  {dd['from']:6.2f}-{dd['to']:6.2f}  voice {dd['voice_lufs']:6.1f}  music under the voice {dd['music_under_voice_lufs']:6.1f}  "
              f"difference {dd['voice_minus_music_db']:5.1f} dB  (duck {dd['duck_db']:4.1f} dB)")
    print(f"effects: median {report['sfx_median_lufs']} momentary LUFS, {report['sfx_under_voice_db']} dB under the voice "
          f"(gain {report['sfx_gain_db']} dB); music at the final hit: {report['music_at_hit_db']} dB")
    print("raw", m0, "| before the limiter", m1, "| FINAL", m2)
    print(f"voice over everything else (400 ms inside the sentences): median {report['voice_over_rest_median_db']} dB, "
          f"minimum {report['voice_over_rest_min_db']} dB at {report['voice_over_rest_min_at']} s; "
          f"windows with the voice under: {report['windows_with_voice_under']} of {report['windows_measured']}")


if __name__ == "__main__":
    main()
