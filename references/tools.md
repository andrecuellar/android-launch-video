# Tools index

Paths are relative to the work dir created by `tools/setup.sh`. Python scripts run as
`venv/bin/python -I <script>` (the capture helpers also work with the system `python3`). Machine
values come from `config.json` through `kitconfig.py` / `kitconfig.mjs`.

## Root

| Tool | Purpose |
| --- | --- |
| `setup.sh <dir> [--skip-install]` | Lives in the skill only: creates a work dir from these tools. |
| `config.example.json`, `kitconfig.py`, `kitconfig.mjs` | Configuration and its readers (`python3 kitconfig.py <key>` prints a value). |
| `requirements.txt` | numpy, scipy, faster-whisper. |

## `capture/`

| Tool | Purpose |
| --- | --- |
| `capture.py` | `ClipGPU`: GPU capture (ddagrab + hardware encoder) with every tap and swipe logged. |
| `clip.py` | `Clip`: same with screenrecord, for tests only (does not reach 60 fps). |
| `sync60.py <name>`, `sync.py <name>` | Align the tap log with the video by the visual change of each action. |
| `measure2.py <video> [y0:y1]`, `measure.py`, `measure_quick.py` | Unique frames per second while there is motion. |
| `PACKAGE=<pkg> app_fps.sh "<actions>" <label>` | SurfaceFlinger timestats of the app layer. |
| `PACKAGE=<pkg> sf_latency.py <x> <y1> <y2> <ms>` | Presentation intervals of the app layer after a swipe. |
| `gpu_test.py <rotate\|native> <name> [mover.sh]` | Test capture to measure the screen corner. |
| `ui.py dump \| tap <text> [n] \| find <text> [n]` | uiautomator hierarchy and tap by text. |
| `demo.sh`, `screencap.sh <out.png>` | Clean status bar (SystemUI demo mode) and a screenshot. |
| `review.sh <name> [every_s]`, `review60.sh` | Duration and contact sheet of a clip. |

## `video/film/`

| Tool | Purpose |
| --- | --- |
| `core.js` | Film engine: closed-form springs, tracks, odometer, cues. The page contract is in `references/film.md`. |

## `video/scripts/`: material, render, review

| Tool | Purpose |
| --- | --- |
| `clips60.sh [clips_folder]` | Runs `clips.py` and `motion.py` into `video/material60/`. |
| `clips.py <clips> <material>` | Unique frames and their times, `clips.js`. |
| `motion.py <material> [clip...]` | Per-frame difference and motion spans, `motion.json`. |
| `still.py`, `settled.py`, `period.py` | Still moments, settled states, loop period of an in-app animation. |
| `segment.mjs`, `final.sh`, `final2.sh`, `draft.sh`, `resources.sh` | Segment render, final render, draft, and how many browsers fit in memory. |
| `sheet.mjs`, `snap.mjs`, `clipsheet.py`, `clipstrip.py`, `rects.py`, `keyframe.py` | Contact sheets, single frames (and `--cues` export), marked crops and key frames of a clip. |
| `overlaps.mjs`, `boxes.mjs`, `point.mjs`, `purity.mjs`, `errors.mjs`, `screens.mjs`, `transform.mjs`, `reading.mjs` | Film checks over `window.boxes`, `window.seek` and friends. |
| `jumps.py`, `stutter.py`, `diffs.py`, `edges.py`, `joins.py` | Frozen frames, jumps, stutter and segment joins in the render. |
| `compare.py`, `diffpng.py`, `measure_boxes.py`, `alpha.py`, `samples.py` | Replica against crop, image differences, boxes, colors and alpha. |
| `store_shots.mjs`, `png_srgb.py` | Clean stills for the store and 24-bit sRGB PNG without alpha. |
| `deliverables.sh <16x9\|9x16> <final.mp4>` | One frame per second, key stills and a light preview. |

## `video/scripts/`: audio

| Tool | Purpose |
| --- | --- |
| `grid.py <track> <grid.json>` | Exact beat grid, kick offsets and key of sections. |
| `audio.py <track> <cues.json> <out_dir> [duration]` | Edit of the track, synthesized effects on the beat, mix at -14 LUFS. |
| `fingerprint.py`, `music_check.py <track> <music.wav> [previous]` | Vocal-chop fingerprint and the 0.88 check on every beat. |
| `hit_shape.py`, `midband_beats.py`, `midband_variants3.py`, `band_levels.py`, `track_spectrum.py` | Locate and describe hits in the track. |
| `chroma_bars.py`, `key_detect.py`, `bass.py` | Harmony per bar, key, bass notes. |
| `audio_offset.py <video.mp4> <mix.wav>` | Audio offset in a rendered MP4. |

## `video/narration/`

| Tool | Purpose |
| --- | --- |
| `tts.py <model> <voice> <prompt.txt> <out.wav>`, `example-prompt.txt` | One Gemini TTS request, logged, key only from `GEMINI_API_KEY`. |
| `transcribe.py <wav> <script.txt> <out.json> [hint]` | faster-whisper transcript and diff against the script. |
| `pace.py`, `segment.py`, `place.py`, `timing_table.py` | Pace, sentences, placement in the film windows, real timing table. |
| `narrated_mix.py`, `check_margin.py`, `audio_artifacts.py`, `formants.py` | Narrated mix and its checks. |

## `music/`

| Tool | Purpose |
| --- | --- |
| `tracks.json`, `list.txt`, `analysis.json` | Mixkit catalog metadata (no audio) and its analysis. |
| `analyze.py mp3/*.mp3`, `grid.py <track>` | Tempo, regularity, energy arc; quick beat grid with energy per bar. |

## `delivery/`

| Tool | Purpose |
| --- | --- |
| `split.sh <master.mp4> <parts_folder> ["Title"]` | 14 MB parts and the JSON entry for the download page. |
| `downloads/index.html` | Artifact page that reassembles each master, verifies SHA-256 and saves it. |

## `editor/`

| Tool | Purpose |
| --- | --- |
| `package.json` | playwright-core 1.48.2. |
| `render.mjs` | Minimal frame-by-frame renderer for a standalone `scene.html`. |
| `gpu-test.mjs` | CPU vs GPU rendering speed of Chromium on this machine. |
| `test-downloads.mjs` | Tests the download page with a stand-in for the capability. |

## `windows/` (copy to `windows_tools_dir`)

| Tool | Purpose |
| --- | --- |
| `display.ps1 status\|portrait\|restore [-Test]` | Rotate the primary monitor and restore it exactly. |
| `window.ps1 list\|move\|place\|top\|normal` | Find and pin the emulator window. |
| `temperatures.ps1 [-Lhm <dll>]` | CPU (Core Temp) and AMD GPU (LibreHardwareMonitor) temperatures. |
