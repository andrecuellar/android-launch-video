"""Transcribes a voice with Whisper large-v3 (faster-whisper, CPU, int8) with per word timings and compares it with
the script. No initial prompt by default: the brand name is not suggested so that the pronunciation test is not biased.

Usage: venv/bin/python -I transcribe.py <voice.wav> <script.txt> <out.json> [initial prompt]
Without an initial prompt it is the strict test; with "Brand." the model gets the brand name as vocabulary.

The model is not bundled: download https://huggingface.co/Systran/faster-whisper-large-v3 and set
"whisper_model_dir" in config.json to its folder.
"""
import difflib
import json
import re
import subprocess
import sys

import numpy as np

from faster_whisper import WhisperModel

sys.path.insert(0, "/PATH/TO/WORKDIR")
from kitconfig import cfg

MODEL = cfg("whisper_model_dir")
LANGUAGE = "es"  # Whisper language code of the voice; change it for other languages
# Words whose timing and probability are printed (normalized, lowercase), e.g. the parts of the brand name.
CHECK_WORDS = ("brand",)


def normal(p):
    """Word for comparison: lowercase and without punctuation; accents are kept (they count as a difference).
    The character class is tuned for Spanish; adapt it for other languages."""
    return re.sub(r"[^\wáéíóúüñ]", "", p.lower())


def main():
    voice, script_path, out = sys.argv[1:4]
    prompt = sys.argv[4] if len(sys.argv) > 4 else None  # optional initial prompt (vocabulary), e.g. "Brand."
    script = open(script_path, encoding="utf-8").read()
    model = WhisperModel(MODEL, device="cpu", compute_type="int8", cpu_threads=8)
    # the audio is decoded with ffmpeg (16 kHz mono) and passed as an array, so faster-whisper does not depend on PyAV
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", voice, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32).copy()
    segments, info = model.transcribe(audio, language=LANGUAGE, beam_size=5, word_timestamps=True, vad_filter=False,
                                      condition_on_previous_text=False, temperature=0.0,
                                      initial_prompt=prompt)
    words, segs = [], []
    for s in segments:
        segs.append({"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip(), "avg_logprob": round(s.avg_logprob, 3),
                     "no_speech_prob": round(s.no_speech_prob, 3), "compression": round(s.compression_ratio, 2)})
        for w in s.words:
            words.append({"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3), "prob": round(w.probability, 3)})
    text = " ".join(s["text"] for s in segs)
    ref = [normal(p) for p in script.split() if normal(p)]
    hyp = [normal(p["word"]) for p in words if normal(p["word"])]
    diff = [d for d in difflib.ndiff(ref, hyp) if d[0] in "+-"]
    json.dump({"text": text, "segments": segs, "words": words, "diff_with_script": diff,
               "language": info.language, "duration": info.duration}, open(out, "w"), indent=1, ensure_ascii=False)
    print("TRANSCRIPT:", text)
    print("differences with the script (- missing, + extra):", diff if diff else "none")
    for p in words:
        if any(w in normal(p["word"]) for w in CHECK_WORDS):
            print(f"   \"{p['word']}\" {p['start']:.2f}-{p['end']:.2f} s, prob {p['prob']:.2f}")


if __name__ == "__main__":
    main()
