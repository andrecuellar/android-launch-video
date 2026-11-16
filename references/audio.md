# Music, sound effects and mix

## Choosing the track

- Mixkit, under the Mixkit Stock Music Free License (https://mixkit.co/license/). Credit title and
  author. No audio is bundled: `tools/music/tracks.json` lists title, author, genre, length and
  link of 263 tracks, `list.txt` the links that were analyzed and `analysis.json` the result of
  `music/analyze.py` (bpm, regularity, median dB, dB range, drop position and jump, kick strength).
- Download candidates into `music/mp3/` and run `venv/bin/python music/analyze.py music/mp3/*.mp3 > music/analysis.json`.
- Pick for energy arc and a stable beat, then let the reviewer listen before any editing.
- `music/grid.py track.mp3 > grid.json` gives a quick grid (tempo, first-beat phase, energy per
  bar) to find drops and endings.

## Beat grid

`venv/bin/python -I video/scripts/grid.py track.mp3 grid.json` measures the exact tempo, phase,
the offset of every kick peak against the grid and the key of the drop and ending sections. The
film's script by bars is written on this grid, and every edit point sits on a bar line.

## Edit (`audio.py`)

```bash
node video/scripts/snap.mjs 16x9 - 1 png --cues cues.json     # export the film's cues
AUDIO_STEMS=1 venv/bin/python -I video/scripts/audio.py track.mp3 cues.json video/audio [duration]
```

- `SECTIONS` (film from, track from, treatment) at the top of `audio.py` are example values
  from a past production: rewrite them for your track and grid. Each section starts on a bar line.
- Joins: equal-power crossfades of about 14 ms that end 10 ms before the kick peak of the incoming
  section, in the dip of the outgoing one, so the incoming kick masks the join.
- Treatments: `echo` lowers, band by band, the tail of a removed vocal hit to the level of a clean
  reference bar; `tail` lowers a band before and after the final hit, keeping its attack intact.
  Both only reduce, never boost.
- Outputs in `video/audio/`: `mix.wav` (final, 48 kHz 24-bit), `music.wav`, `sfx.wav`,
  `measurement.txt`, `sfx-peaks.json` (`{t, type, peak_at, level_dbfs}` per effect). With
  `AUDIO_STEMS=1` also `music-only.wav`, `sfx-rest.wav` and `sfx-final.wav` for the narrated mix.

## Cue types

The film registers cues with `cue(t, type, extra)` (`core.js`); `audio.py` synthesizes one effect
per cue and places it so that **its measured peak** lands on `t`. Effects are tuned to the track's
scale (the example uses a minor pentatonic measured from the bass: set yours with
`key_detect.py` / `bass.py`).

| type | extra fields |
| --- | --- |
| `tap`, `release` | |
| `pop` | `note`, `strength` |
| `tick`, `odometer_tick` | `note` |
| `stretch` | `down`, `soft` |
| `sweep` | `dur`, `up`, `strength` |
| `hit` | `strength`, `final` |
| `word` | `note` |
| `compress`, `headline`, `badge`, `confirm`, `notification`, `underline` | |
| `drag` | `dur` |

Unknown types are skipped. A `sweep` within 0.45 s before the `hit` with `final` is reinforced and a
riser is added before that hit.

## Vocal-chop check

Some stock tracks carry a layer of chopped vocal hits that sound like words to the ear, sometimes
rude ones, at a few points of the track.

1. Find them by ear and with `hit_shape.py`, `midband_beats.py`, `band_levels.py`,
   `track_spectrum.py` (spectrogram) around the suspect bars.
2. `fingerprint.py` builds the hit's fingerprint: 40 log-spaced bands from 250 Hz to 6 kHz.
3. `venv/bin/python -I video/scripts/music_check.py track.mp3 video/audio/music.wav [previous]`
   compares, with cosine similarity, the fingerprint against every beat and half beat of the edit.
   **No beat may reach 0.88.** Bars that do stay out of the edit; their echoes are lowered.
4. `chroma_bars.py`, `key_detect.py`, `bass.py` and `midband_variants3.py` help pick clean
   replacement bars with the same harmony.

## Mix and master

- Starting point: track x 0.5 + effects x 0.62.
- Master to -14 LUFS integrated, true peak <= -1 dBTP (AAC 48 kHz in the final MP4).
- `audio_offset.py <video.mp4> <mix.wav>` checks the audio in the rendered MP4 is not shifted.
