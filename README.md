# android-launch-video

A Claude Code skill to produce an agency-quality promo video for an Android app, from the **real
app recorded at 60 fps** in an emulator:

- Google Play video, 1920x1080, 60 fps
- Vertical 9:16 cut for Reels, Shorts and TikTok
- Each with and without an AI voice-over
- Play screenshots, feature graphic and social stills

It is a method (`SKILL.md` and `references/`) plus a toolkit (`tools/`): GPU capture with tap
logging, an HTML film engine rendered frame by frame with Playwright, music on a measured beat grid
with a vocal-chop check, Gemini TTS narration verified with faster-whisper, quality checks and a
mobile-friendly download page.

## Requirements

- **[product-launch-motion](https://github.com/AbubakrChan/product-launch-motion)** by AbubakrChan
  (MIT), installed as a Claude Code skill. Tested at commit `edbfb105`. This skill builds on its
  film technique and does not bundle it. Read `SKILL.md`, `references/technique.md`,
  `references/prompts.md`, `legacy/references/03-word-locked-sync.md` and
  `legacy/references/07-sound-and-master.md` from it.
- Windows 10/11 with WSL2 (Ubuntu), a GPU with a hardware encoder that ffmpeg supports
  (`hevc_amf` tested; NVENC configured but untested), and a monitor you can rotate to portrait.
- On Windows: the Android SDK emulator, an ffmpeg build with `ddagrab`.
- In WSL: Python 3.10+, Node 18+, ffmpeg/ffprobe, adb, `systemd-run --user` for capped renders.
- A Gemini API key for narration (free tier works, with a small daily quota).
- About 3 GB for the faster-whisper large-v3 model.

## Install

```bash
# 1. The required film skill
git clone https://github.com/AbubakrChan/product-launch-motion ~/.claude/skills/product-launch-motion

# 2. This skill
git clone https://github.com/andrecuellar/android-launch-video ~/.claude/skills/android-launch-video
```

## Quick start

```bash
# A work dir per production (copies the tools, fills in paths, venv, Node deps, Chromium)
~/.claude/skills/android-launch-video/tools/setup.sh ~/videos/my-app
cd ~/videos/my-app
$EDITOR config.json        # emulator serial, Windows paths, screen corner, encoder

# Whisper model for the voice checks (not bundled)
venv/bin/pip install "huggingface_hub[cli]"
venv/bin/huggingface-cli download Systran/faster-whisper-large-v3 --local-dir models/faster-whisper-large-v3

# Narration key: only from the environment, never in a file inside the work dir
export GEMINI_API_KEY=...
```

Then ask Claude Code for the video ("make the Play promo video for this app"); the skill drives
the rest: analysis, storyboard and approvals, capture, film, music, narration, checks and delivery.
`setup.sh <dir> --skip-install` only copies and configures.

## Configuration

`config.json` (from `tools/config.example.json`) holds every machine-specific value: emulator
serial and AVD, Windows SDK path, optional wrapper to run `.exe` files from WSL, PowerShell path,
ffmpeg.exe and capture folders, screen corner and capture size, rotation filter, encoder and its
arguments, Chromium path (empty uses Playwright's), Whisper model folder and the folder for master
copies. Any key can be overridden with `ALV_<KEY>` environment variables.

## What is in here

| Path | Contents |
| --- | --- |
| `SKILL.md` | The method and the production rules |
| `references/` | Capture, film, audio, narration, store assets, checks, lessons, tools index |
| `tools/capture/` | 60 fps GPU capture, tap log and sync, smoothness measurements, adb helpers |
| `tools/video/film/core.js` | Film engine: pure `seek(t)`, closed-form springs, rolling digits |
| `tools/video/scripts/` | Material prep, render, review sheets, film checks, soundtrack and music analysis, store stills |
| `tools/video/narration/` | Gemini TTS, Whisper checks, line placement, narrated mix |
| `tools/music/` | Mixkit catalog metadata and analysis (no audio) |
| `tools/delivery/` | Split masters into parts and a download page that reassembles and verifies them |
| `tools/windows/` | PowerShell: rotate the monitor, place the emulator window, read temperatures |
| `tools/editor/` | Playwright runtime and helper tests |

## Credits: yours vs third-party

Everything in this repository is original work under the MIT license. It depends on, but does not
include:

- **product-launch-motion** by AbubakrChan (MIT): the film technique this skill adapts.
  https://github.com/AbubakrChan/product-launch-motion
- **Mixkit** music, under the Mixkit Stock Music Free License: https://mixkit.co/license/. Only
  titles, authors and links are listed; credit the track you use.
- **Gemini API** (Google) for text-to-speech, under Google's terms.
- **faster-whisper** (SYSTRAN, MIT) and the Whisper large-v3 weights (OpenAI, MIT) converted by
  SYSTRAN: https://huggingface.co/Systran/faster-whisper-large-v3
- **Playwright** (Microsoft, Apache-2.0).
- **FFmpeg** (LGPL/GPL, depending on the build).
- **scrcpy** (Genymobile, Apache-2.0), for the untested physical-phone path.
- Core Temp and LibreHardwareMonitor (MPL-2.0) are optional, for temperature readings.

## Limitations

- Tested only on Windows 11 + WSL2 with an AMD GPU (`hevc_amf`). The NVENC settings are untested.
- The physical-phone path with scrcpy is documented but **untested**.
- macOS and Linux capture are not covered.
- Several scripts keep constants tuned for one past production (track sections, segment cuts,
  time windows, film length). They are marked in the code: adapt them to your film.
- The narration timing helpers count syllables for Spanish; adapt them for other languages.
- The film page (`video/film/index.html`) is written per production; the tools define its
  contract (`references/film.md`).

## License

MIT. Copyright (c) 2026 andrecuellar.
