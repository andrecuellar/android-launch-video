"""Cuts the take into sentences at its silences. Energy VAD (10 ms, threshold relative to the voice level), minimum
silence 120 ms; every Whisper word is assigned to the voice span it overlaps most, and every script sentence goes from
its first to its last word. The script has one sentence per line, and the transcript must already match it word by
word (check diff_with_script of transcribe.py first).
Usage: segment.py <take.wav> <transcript.json> <script.txt> <out.json>"""
import json, re, subprocess, sys
import numpy as np
SR = 48000
path, transcript_path, script_path, out = sys.argv[1:5]
c = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(c, dtype=np.float32).astype(np.float64)
H = int(0.010 * SR)
rms = np.array([np.sqrt(np.mean(x[i:i + H] ** 2)) for i in range(0, len(x) - H, H)])
db = 20 * np.log10(rms + 1e-9)
ref = np.percentile(db[db > -60], 90) if np.any(db > -60) else -20
voiced = db > ref - 38
# close gaps shorter than 120 ms and remove islands shorter than 60 ms
def runs(b):
    out, i = [], 0
    while i < len(b):
        j = i
        while j < len(b) and b[j] == b[i]: j += 1
        out.append((b[i], i, j)); i = j
    return out
for v, i, j in runs(voiced):
    if not v and (j - i) < 12 and i > 0 and j < len(voiced): voiced[i:j] = True
for v, i, j in runs(voiced):
    if v and (j - i) < 6: voiced[i:j] = False
spans = [(i * H / SR, j * H / SR) for v, i, j in runs(voiced) if v]
tr = json.load(open(transcript_path)); words = tr["words"]
norm = lambda p: re.sub(r"[^\wáéíóúüñ]", "", p.lower())  # tuned for Spanish; adapt for other languages
lines = [l.strip() for l in open(script_path, encoding="utf-8") if l.strip()]
# assign words to lines in order (the transcript already matches the script word by word)
k = 0; line_of = []
for li, l in enumerate(lines):
    n = len([w for w in l.split() if norm(w)])
    line_of += [li] * n
    k += n
# every voice span goes to the line of the word it overlaps most (or the closest one)
assigned = {}
for ti, (ta, tz) in enumerate(spans):
    best, overlap = None, -1e9
    for wi, w in enumerate(words[:len(line_of)]):
        s_ = min(tz, w["end"]) - max(ta, w["start"])
        if s_ > overlap: best, overlap = line_of[wi], s_
    assigned.setdefault(best, []).append((ta, tz))
sentences = []
for li, l in enumerate(lines):
    sel = sorted(assigned.get(li, []))
    ws = [w for wi, w in enumerate(words[:len(line_of)]) if line_of[wi] == li]
    start, end = sel[0][0], sel[-1][1]
    pauses = [(round(sel[m][1], 3), round(sel[m + 1][0], 3)) for m in range(len(sel) - 1)]
    sentences.append({"text": l, "start": round(start, 3), "end": round(end, 3), "dur": round(end - start, 3), "inner_pauses": pauses,
                      "words": [{"word": w["word"], "start": w["start"], "end": w["end"]} for w in ws]})
for f in sentences:
    pi = sum(b - a for a, b in f["inner_pauses"])
    print(f"{f['start']:6.2f}-{f['end']:6.2f}  lasts {f['dur']:4.2f} s (inner pauses {pi:4.2f} s)  {f['text']}")
json.dump({"voice_spans": spans, "sentences": sentences}, open(out, "w"), indent=1, ensure_ascii=False)
