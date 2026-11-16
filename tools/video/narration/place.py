"""Places the sentences of the take in their film windows and writes the voice alone (48 kHz) and the timing table.

Every sentence is cut at its silences (the sentences file from segment.py) with 40 ms of air before and 80 ms
after (without touching the neighbor sentence) and 8 ms fades at the edges, which fall in silence. Some sentences are
split at their inner pauses so that the keyword lands on the visual change it names. No time stretching, except
atempo <= 1.06 where a sentence does not fit (it is reported in the table).

Usage: venv/bin/python -I place.py <take.wav> <sentences.json> <out_voice.wav> <out_table.json>
"""
import json
import subprocess
import sys

import numpy as np

SR = 48000
DUR = 41.0  # film duration (s); example value: set it to your film
AIR_BEFORE, AIR_AFTER, FADE = 0.04, 0.08, 0.008

# Script windows (s) and placement rules, one entry per sentence in script order.
# "anchors": (word, film time) or ("start", film time); a word anchor matches the first word of the sentence that
# starts with it (normalized, lowercase).
# "parts": indexes of the inner pauses where the sentence is split; every part carries its own anchor.
# Optional: "pause_max" (s) shortens longer inner pauses; "atempo" (<= 1.06) speeds up a sentence that does not fit.
PLAN = [  # example: replace it with the windows of your script
    {"window": (0.4, 3.6), "anchors": [("start", 0.40)], "visual": "the opening question comes in one word per beat"},
    {"window": (4.3, 6.0), "anchors": [("start", 4.30)], "visual": "headline of the first scene from 4.1 s"},
    {"window": (12.3, 15.6), "anchors": [("keyword", 13.20)], "visual": "the keyword lands on the visual change it names, at 13.2 s"},
    {"window": (28.3, 34.5), "parts": [0], "anchors": [("start", 28.30), ("second", 30.10)],
     "visual": "sentence split at its inner pause: every part with its own anchor"},
]


def read(path, sr):
    c = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-af", "aresample=resampler=soxr:precision=28",
                        "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(c, dtype=np.float32).astype(np.float64)


def atempo(x, f):
    p = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "f64le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", f"atempo={f}",
                        "-f", "f64le", "-"], input=x.tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float64).copy()


def norm(p):
    """Lowercase without punctuation; the character class is tuned for Spanish, adapt it for other languages."""
    import re
    return re.sub(r"[^\wáéíóúüñ]", "", p.lower())


def main():
    take, sentences_path, out_voice, out_table = sys.argv[1:5]
    x = read(take, SR)
    data = json.load(open(sentences_path))
    sentences = data["sentences"]
    voice = np.zeros(int(DUR * SR))
    table = []
    for k, (fr, plan) in enumerate(zip(sentences, PLAN)):
        pauses = fr["inner_pauses"]
        cuts = [fr["start"]] + [p for i in plan.get("parts", []) for p in pauses[i]] + [fr["end"]]
        parts = [(cuts[2 * j], cuts[2 * j + 1]) for j in range(len(cuts) // 2)]
        # limits for the air: do not go into the neighbor sentence
        lim_a = sentences[k - 1]["end"] + 0.02 if k else 0.0
        lim_z = sentences[k + 1]["start"] - 0.02 if k + 1 < len(sentences) else len(x) / SR
        for j, (a, z) in enumerate(parts):
            anchor = plan["anchors"][j]
            a0, z0 = max(lim_a, a - AIR_BEFORE), min(lim_z, z + AIR_AFTER)
            if j + 1 < len(parts): z0 = min(z0, (z + parts[j + 1][0]) / 2)
            if j > 0: a0 = max(a0, (parts[j - 1][1] + a) / 2)
            piece = x[int(a0 * SR):int(z0 * SR)].copy()
            # shorten long inner pauses (only if the plan asks for it)
            trimmed = 0.0
            if plan.get("pause_max") is not None:
                for pa, pz in [q for q in pauses if a < q[0] < z]:
                    extra = (pz - pa) - plan["pause_max"]
                    if extra > 0:
                        c0 = int((pa - a0 + plan["pause_max"] / 2) * SR); c1 = c0 + int(extra * SR)
                        w = int(0.006 * SR)
                        f_out = np.linspace(1, 0, w); f_in = np.linspace(0, 1, w)
                        piece[c0 - w:c0] *= f_out; piece[c1:c1 + w] *= f_in
                        piece = np.concatenate([piece[:c0], piece[c1:]]); trimmed += extra
            f = plan.get("atempo", 1.0)
            if f != 1.0:
                piece = atempo(piece, f)
            w = int(FADE * SR)
            piece[:w] *= np.linspace(0, 1, w); piece[-w:] *= np.linspace(1, 0, w)
            # position: the anchor (voice start or a word) lands on its time
            voice_offset = (a - a0) / f  # from the edge of the piece to the start of the voice
            if anchor[0] == "start":
                t_voice = anchor[1]
            else:
                word = next(p for p in fr["words"] if norm(p["word"]).startswith(anchor[0]))
                rel = max(0.0, word["start"] - a)
                if trimmed and word["start"] > a: rel -= trimmed if any(a < q[0] < word["start"] for q in pauses) else 0
                t_voice = anchor[1] - rel / f
            start = t_voice - voice_offset
            i0 = int(round(start * SR))
            voice[i0:i0 + len(piece)] += piece
            voice_dur = ((z - a) - trimmed) / f
            table.append({"sentence": k + 1, "part": j + 1, "text": fr["text"] if len(parts) == 1 else None, "take_from": round(a, 3), "take_to": round(z, 3),
                          "voice_from": round(t_voice, 3), "voice_to": round(t_voice + voice_dur, 3), "window": plan["window"], "atempo": f,
                          "trimmed_pause_s": round(trimmed, 3), "anchor": anchor, "visual": plan["visual"]})
    peak = np.abs(voice).max()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f64le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_s24le", out_voice],
                   input=voice.tobytes(), check=True)
    json.dump(table, open(out_table, "w"), indent=1, ensure_ascii=False)
    for r in table:
        inside = r["window"][0] - 0.005 <= r["voice_from"] and r["voice_to"] <= r["window"][1] + 0.005
        print(f"sentence {r['sentence']:2d}.{r['part']}  {r['voice_from']:6.2f}-{r['voice_to']:6.2f} s  window {r['window'][0]:.1f}-{r['window'][1]:.1f}  "
              f"{'inside' if inside else 'OUTSIDE'}  atempo {r['atempo']}  trimmed pause {r['trimmed_pause_s']:.2f} s  anchor {r['anchor']}")
    print(f"peak of the voice alone: {20 * np.log10(peak):.1f} dBFS")


if __name__ == "__main__":
    main()
