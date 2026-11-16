---
name: android-launch-video
description: Produce an agency-quality promo video for an Android app from the REAL app recorded at 60 fps in an emulator, plus the Google Play store assets. Use when asked for a Play Store promo video, app trailer, launch film, product video for social (Reels, Shorts, TikTok), vertical 9:16 app video, video with or without AI voice-over, Play listing screenshots, feature graphic, or "make a video of my Android app". Covers real 60 fps capture (Windows host GPU via ffmpeg ddagrab), touch indicators instead of a cursor, an HTML film rendered frame by frame with Playwright, licensed music on a measured beat grid with a vocal-chop check, Gemini TTS narration verified with faster-whisper, quality controls and delivery. Builds on the product-launch-motion skill, which must be installed.
---

# Android launch video

A method and a toolkit to make the Google Play promo video (16:9), the vertical cut for social
(9:16), each with and without voice-over, and the store images, from the real app running in an
emulator. The bar is a finished agency film, not a screen recording.

This skill adapts **product-launch-motion** (by AbubakrChan, MIT) to Android. That skill is a
requirement and is not bundled: install it from https://github.com/AbubakrChan/product-launch-motion
(tested at commit `edbfb105`) and read, before writing any film code:

- `SKILL.md`
- `references/technique.md`
- `references/prompts.md`
- `legacy/references/03-word-locked-sync.md`
- `legacy/references/07-sound-and-master.md`

What changes for Android: touch indicators instead of a cursor, real 60 fps capture instead of
rebuilt motion, opaque surfaces for everything lifted off the screen, music checked for vocal-chop
artifacts, narration verified by speech recognition, and the Play store rules.

The tools live in `tools/` (index in `references/tools.md`). Long detail lives in `references/`;
this file is the method and the rules.

## 1. Deliverables

| Piece | Spec |
| --- | --- |
| Play / YouTube video | 1920x1080, 60 fps, H.264, AAC 48 kHz, -14 LUFS integrated, true peak <= -1 dBTP |
| Social vertical video | 1080x1920, same specs, composed on its own (never a crop of the 16:9) |
| Each with and without voice-over | Four masters. The narrated cut is made separately and **never replaces** the music-only cut |
| Play screenshots | Up to 8, 1080x1920, 24-bit PNG without alpha (or JPEG) |
| Feature graphic | 1024x500 without alpha; keep the center (about x 362 to 662) free: Play puts the play button there |
| Social stills | 1080x1920 |
| Previews | 14 MB max each, to show them in an Artifact |

Length: about 40 s, never more than 50 s.

In the 9:16, nothing important (text, logo, button) in the bands that Reels, Shorts and TikTok
cover with their UI: the top 14 %, the bottom 20 % and about 120 px from the right edge.

## 2. Production rules (approve them, then hold them)

- **Finished product.** Judge every frame as a paid agency film.
- **Real motion.** Everything that moves inside the phone is the app recorded at 60 fps. No motion
  is rebuilt from animated screenshots. A clip that stutters is recorded again.
- **No cursor.** Android has no mouse. Each touch is marked with a soft disc and the Material ripple,
  at the place and moment of the real touch (from the tap log of the capture).
- **No other app on screen** (messaging apps, maps, browser, account picker). If the app names
  another app on a button, the word may be read; the other app never appears.
- **Nothing floats without a surface.** Anything lifted off the phone screen sits on its own opaque
  surface: the card itself or the app's container for that section, with its radius, color and a
  soft shadow. No text rests over the phone, and no text overlaps another.
- **Identical to the app.** A lifted element starts as an exact crop of the visible frame and, in
  the air, crosses with a short blur to a vector replica calibrated against that crop. No invented
  badges, icons, buttons or data.
- **Nothing that is not in the brand or the app.** No play glyph on the final button, no
  full-screen color wipes, no box behind a text to make it readable: adjust sizes instead.
- **The brand opens and closes**, centered on its axis in both formats.
- **Living motion.** Long strokes that stretch, thin out and cross on the beat read better than
  stiff blocks.
- **Believable data**: real market values for the app's domain, never real personal data.
- Copy in the listing's language with correct diacritics, no em-dashes.
- The reviewer approves the script, the music, the voice and the brand pronunciation **before**
  production, and sees nothing that was not checked first (section 11).

## 3. Roles and approvals

- **Director** (the main session): talks with the reviewer, launches subagents, reviews and
  publishes. Questions to the reviewer go through AskUserQuestion.
- **Analysis subagent**: product, brand, flows, local environment, sample data, recording plan and
  script. It does not build the app or start the emulator.
- **Approvals**: storyboard in an Artifact (key frames drawn with Playwright and looked at before
  showing them), script by bars, music, voice casting, brand pronunciation, and permission to
  rotate the monitor while recording.
- **Production subagent**: build, emulators, capture, film, audio, narration, render, stills,
  checks and deliverables. It logs progress in `PROGRESS.md` in the work dir.
- **Close**: the director reviews and publishes; reviewer notes go back to production
  (SendMessage) until approved.

## 4. Local environment and data

- **Local emulators only.** Before seeding, check that every emulator host variable is set: a
  seed through an admin SDK with one variable missing writes to production.
- **Believable data** for the target market: names, places, prices and photos. Photos with a
  license that allows commercial use, source noted, no third-party brands.
- **Location**: `adb -s <serial> emu geo fix <longitude> <latitude>`.
- **Release or profile build**, without debug overlays and pointed at the emulators. A patch that
  only exists for recording (hide an environment banner, skip a wait) stays uncommitted and is
  reverted at the end.
- **Telemetry** (crash reporting, analytics) off in that build, or proven not to reach production.
- **Clean status bar** with the SystemUI demo mode (`tools/capture/demo.sh`): 9:41, full battery and
  wifi, no notifications.
- **System animation scales at 1** while recording; at 0 the app does not move like a phone.
- **Shared backends**: if anything shared (a staging database) receives writes, count rows before
  and after. A local API with simulated providers can leave invented data in a shared database.

## 5. Real 60 fps capture

`screenrecord` inside the emulator is not enough: about 41 fps at 1080x2400 (53 at 720x1600), and
scrolls look choppy. Use it only for tests (`tools/capture/clip.py`). Options:

1. **Windows host + GPU (tested).** Emulator on Windows with `-gpu host`, the monitor rotated to
   portrait so the phone fits at 1:1, ffmpeg's `ddagrab` (Desktop Duplication) at 60 fps cropped to
   the phone screen and rotated, encoded almost lossless with `hevc_amf` (AMD; tested) or
   `h264_nvenc` / `hevc_nvenc` (NVIDIA; untested). `tools/capture/capture.py` (`ClipGPU`) records,
   logs every tap and swipe with the emulator clock, and moves the clip to WSL.
2. **Physical phone with scrcpy (UNTESTED).** `scrcpy --record` at the phone's refresh rate; the tap
   log and sync would need adapting.
3. **macOS / Linux hosts**: not covered.

Then `sync60.py` aligns each tap with the visual change it causes, `measure2.py`, `stutter.py` and
`jumps.py` measure the result (the tested setup gave 53 to 59 unique frames per second), and
`app_fps.sh` tells whether the app itself draws at 60 inside the emulator. Step by step, with the
Windows checks (unlocked session, screen timeout, free memory): `references/capture-60fps.md`.

## 6. The film

Write `DIRECTION.md` (brand colors and fonts from the app theme, logo, concept, script by bars,
rules), then `PLAN.md`, and only then code. One HTML page (`film/index.html?f=16x9` or `?f=9x16`)
where everything is a pure function of `seek(t)`: closed-form springs, no CSS transitions, no
timers. `tools/video/film/core.js` is the engine (springs, tracks, rolling digits). Inside a generic
vector phone frame (no maker branding) only the real recording plays, frame by frame from
`seek(t)`, with the touch indicators drawn from the tap log.

Render with Playwright: 4 subframes per frame averaged with ffmpeg `tmix` at 60 fps, in parallel
segments sized to free memory. Drafts at 30 fps and half scale. Contact sheets per bar and single
frames for review. Rolling digits are checked frame by frame: they must never show garbage in
between. Detail: `references/film.md`.

## 7. Music

- **Mixkit** tracks under the Mixkit license (https://mixkit.co/license/); title and author go in
  the credits. The director picks, the reviewer listens before editing. `tools/music/` has a
  catalog (title, author, genre, length, link) and a tempo/energy analysis; no audio is bundled.
- **Own beat grid** (`video/scripts/grid.py`): measured tempo and first-beat phase. Cuts land on the beat with
  equal-power crossfades of about 14 ms in the dip before the attack.
- **Vocal-chop check.** Some tracks carry chopped vocal hits that sound like words (sometimes rude
  ones) to the ear. `fingerprint.py` and `music_check.py` compare the spectral fingerprint of the
  hit (40 log bands from 250 Hz to 6 kHz, cosine similarity) with every beat of the edit: none may
  reach **0.88**. Those bars stay out and their echoes are lowered.
- **Sound effects** synthesized, tuned to the track's scale and placed on the measured peak
  (`audio.py`).
- **Mix** starting point: track x 0.5 + effects x 0.62, -14 LUFS, true peak <= -1 dBTP.
Detail: `references/audio.md`.

## 8. Narration

- **Gemini TTS**, model `gemini-3.8-flash-tts`. The key comes **only** from the environment
  variable `GEMINI_API_KEY`: never printed, never on a command line, never in a repository or a
  chat. `tts.py` sends it only in a header and scrubs it from errors.
- **Few free generations per day.** Every request is logged; a 429 is reported and not retried.
  Budget them: a short casting line per voice, then the whole script in one request per take.
- **Casting**: a natural, warm voice, not robotic. Good candidates: Sulafat (warm), Laomedeia
  (lively), Leda (youthful).
- **Brand pronunciation**: ask the reviewer before generating; it goes in the director's notes of
  the prompt ("pronounced ..., like ..."), never on screen. faster-whisper large-v3
  (`transcribe.py`) checks it with and without a hint. The model is not bundled:
  https://huggingface.co/Systran/faster-whisper-large-v3
- **Voice first.** Each line has its window in the film and its key word lands on the visual change
  it names (`segment.py`, `place.py`, `timing_table.py`, `pace.py`).
- **Narrated mix** (`narrated_mix.py`): the music ducks under each line to 9 to 12 dB below the
  voice, with ramps. `check_margin.py` finds where the voice loses, `audio_artifacts.py` finds
  clicks and cuts.
Detail: `references/narration.md`.

## 9. Store images and Play metadata

- **Screenshots**: clean frames of the 9:16 film (`store_shots.mjs`, a single `seek(t)` per frame,
  no motion blur) or real screens with a headline. 1080x1920, 24-bit PNG without alpha
  (`png_srgb.py`). The first one states the value proposition.
- **Feature graphic** 1024x500: brand, one line and the phone, center kept free.
- **Social stills** 1080x1920, respecting the safe bands of section 1.
- **Play metadata rules**, which also apply to the video: no "#1", "best", awards, testimonials,
  calls to download, dated offers or repeated keywords, and nothing the app does not do.
Detail: `references/store-assets.md`.

## 10. Delivery

- **Main Artifact**: the four previews, the stills, the listing texts and the music credits.
- **One download page per format** (Artifact `downloads` capability). Masters are split in 14 MB
  parts (`tools/delivery/split.sh`), reassembled in the browser and verified with SHA-256 before
  offering to save them (`tools/delivery/downloads/index.html`, tested with
  `tools/editor/test-downloads.mjs`). One publish sends up to 64 MB: upload the parts in several
  batches to the same URL.
- Optionally copy the masters to a Windows folder (`masters_dir_wsl` in the config).
- Upload to Play or social only when the reviewer asks.

## 11. Before showing anything

Look at every contact sheet yourself, at real size and in context, and run the checks of
`references/checks.md`: film (`overlaps.mjs`, `purity.mjs`, `errors.mjs`), render (`jumps.py`,
`stutter.py`), audio (-14 LUFS, true peak, no vocal-shaped hit, full voice per Whisper) and the
visual list (no cursor, no other app, no debug banners, clean status bar, no personal data, no
clipped text, no spelling mistakes).

## 12. Machine care

Before every heavy batch check `uptime`, `free -g` and Windows free memory. Renders run inside a
memory-capped scope, one Gradle build at a time, temperatures watched on long batches (pause
above 85 C CPU or 80 C GPU), Windows never below 2 GB free. Never kill processes or emulators of
other sessions. Detail: `references/checks.md`, section "Machine care".

## 13. Cleanup

Shut down the Android emulator and any other emulators started, restore the monitor and the screen
timeout, revert recording-only patches and temporary config, empty the Windows capture folder, and
state plainly what is still pending.

## References

- `references/capture-60fps.md`: Windows host capture, step by step.
- `references/film.md`: film page contract, engine, render, review sheets.
- `references/audio.md`: music choice, beat grid, vocal-chop check, effects, mix.
- `references/narration.md`: Gemini TTS, casting, Whisper checks, placement, narrated mix.
- `references/store-assets.md`: screenshots, feature graphic, Play rules.
- `references/checks.md`: pre-review checklist and machine care.
- `references/lessons.md`: hard-won lessons, as rules.
- `references/tools.md`: every tool, what it does and how to call it.
