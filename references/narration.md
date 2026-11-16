# Narration

The narrated cut is a separate master. It never replaces the music-only cut.

## Setup

- Gemini API key in the environment only: `export GEMINI_API_KEY=...` (or
  `set -a; source <your env file outside the repo>; set +a`). Never print it, never pass it on a
  command line, never commit it, never paste it in a chat. `tts.py` sends it only in the request
  header and scrubs it from any error it logs.
- Whisper model (not bundled, about 3 GB):

  ```bash
  venv/bin/pip install "huggingface_hub[cli]"
  venv/bin/huggingface-cli download Systran/faster-whisper-large-v3 \
    --local-dir models/faster-whisper-large-v3
  ```

  Its folder is `whisper_model_dir` in `config.json`. It runs on CPU with int8; it is heavy, so
  run one transcription at a time.

## Prompt and casting

- Model `gemini-3.8-flash-tts`. The free tier allows only a few generations per day: every request
  is appended to `video/narration/requests.json`, and a 429 is reported, never retried.
- Write the prompt from `video/narration/example-prompt.txt`: AUDIO PROFILE, THE SCENE,
  DIRECTOR'S NOTES (language and accent, warmth, pace, pauses, and the brand pronunciation:
  "[BRAND] is pronounced ..., like ..."), and the TRANSCRIPT, one line per script sentence.
- Casting: one short line per candidate voice, for the reviewer to choose. A natural, warm voice
  works best; good candidates are Sulafat (warm), Laomedeia (lively) and Leda (youthful).
- Take: the whole script in a single request, so the read is continuous.

```bash
venv/bin/python -I video/narration/tts.py gemini-3.8-flash-tts Sulafat prompt.txt take.wav
```

## Checks with Whisper

```bash
venv/bin/python -I video/narration/transcribe.py take.wav script.txt transcript.json            # no hint
venv/bin/python -I video/narration/transcribe.py take.wav script.txt transcript-hint.json "Brand."
venv/bin/python -I video/narration/pace.py transcript.json script.txt
```

- The transcript must give back the whole script; `diff_with_script` lists the differences.
- The brand must be recognized **without** the hint, not only with it. Set `CHECK_WORDS` in
  `transcribe.py` to the brand's spelling, and `LANGUAGE` (default `"es"`) to the script's language.
- `pace.py` reports spoken length, syllables per second and pauses per line. Its syllable counter
  is tuned for Spanish; adapt it for other languages.
- `audio_artifacts.py take.wav` finds clicks, noise in pauses and abrupt starts or ends;
  `formants.py` helps judge a vowel that sounds off.

## Voice first: placing each line

```bash
venv/bin/python -I video/narration/segment.py take.wav transcript.json script.txt sentences.json
venv/bin/python -I video/narration/place.py take.wav sentences.json placed-voice.wav timing-table.json
venv/bin/python -I video/narration/transcribe.py placed-voice.wav script.txt placed-voice-transcript.json
venv/bin/python -I video/narration/timing_table.py     # run from the folder with those files
```

- `segment.py` cuts the take into sentences at its silences.
- `place.py` puts each sentence into its window of the film (the `PLAN` table: adapt it), with
  40 ms of air before and 80 ms after, 8 ms fades in silence, and splits a sentence at an inner
  pause so its key word lands on the visual change it names (anchors `start`, `keyword`, `second`).
  No time stretching, except `atempo <= 1.06` where a sentence does not fit (reported).
- `timing_table.py` checks the real edges of each sentence (energy) and the key word (Whisper)
  against the window and the visual change.

## Narrated mix

```bash
venv/bin/python -I video/narration/narrated_mix.py placed-voice.wav video/audio \
  video/audio/sfx-peaks.json narrated.wav mix-report.json
venv/bin/python -I video/narration/check_margin.py     # from the folder with its input files
```

- Needs the stems of `audio.py` (`AUDIO_STEMS=1`).
- The music ducks under each line to 9 to 12 dB below the voice, with ramps; effects stay audible
  but never over a word. The final hit and its riser keep their level.
- `check_margin.py` lists where the voice loses against the music.
- Master to -14 LUFS and true peak <= -1 dBTP, like the music-only cut.
- Film length, closing time and hit time (`HIT_TIME`) in these scripts are example values from a
  past production: adapt them.
