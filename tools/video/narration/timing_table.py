"""Real timing table of the placed voice: edges of every sentence by energy (10 ms, threshold 40 dB under the peak)
and the keyword according to Whisper, against the script window and the visual change.
Run it from the folder that holds placed-voice.wav (place.py), timing-table.json (place.py) and
placed-voice-transcript.json (transcribe.py on placed-voice.wav).
Usage: venv/bin/python -I timing_table.py"""
import json, re, subprocess
import numpy as np
SR = 48000
c = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "placed-voice.wav", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(c, dtype=np.float32).astype(np.float64)
H = int(0.01 * SR)
env = np.array([np.sqrt(np.mean(x[i:i + H] ** 2)) for i in range(0, len(x) - H, H)])
act = env > np.abs(x).max() * 10 ** (-40 / 20)
table = json.load(open("timing-table.json"))
words = json.load(open("placed-voice-transcript.json"))["words"]
norm = lambda p: re.sub(r"[^\wáéíóúüñ]", "", p.lower())  # tuned for Spanish; adapt for other languages
KEYWORDS = {1: ("keyword", 1.0), 2: ("second", 4.42)}  # sentence: (keyword, time of the visual change); example
KEYWORD_IN_PART_2 = (11, 12)  # sentences whose keyword is in their second part; example values: adapt them
print("sentence  voice (energy)     window        inside   keyword (Whisper)           visual change   difference")
for r in table:
    a, z = r["voice_from"] - 0.08, r["voice_to"] + 0.08
    i0, i1 = int(a * 100), int(z * 100)
    idx = np.flatnonzero(act[i0:i1])
    va, vz = (i0 + idx[0]) / 100, (i0 + idx[-1] + 1) / 100
    inside = r["window"][0] - 0.01 <= va and vz <= r["window"][1] + 0.01
    key = ""
    k = r["sentence"]
    if k in KEYWORDS and (r["part"] == 1 if k not in KEYWORD_IN_PART_2 else r["part"] == 2):
        w, tv = KEYWORDS[k]
        p = next((p for p in words if norm(p["word"]).startswith(w) and va - 0.45 <= p["start"] <= vz), None)
        if p: key = f"\"{p['word']}\" {p['start']:6.2f} s        {tv:6.2f} s       {p['start'] - tv:+.2f} s"
    print(f"{k:2d}.{r['part']}      {va:6.2f}-{vz:6.2f} s   {r['window'][0]:4.1f}-{r['window'][1]:4.1f}   {'yes' if inside else 'NO '}      {key}")
