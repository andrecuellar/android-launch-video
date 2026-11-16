# Checks before review, and machine care

Nothing goes to the reviewer before these checks pass. Look at the outputs yourself.

## Film

- Contact sheets of every bar in both formats (`sheet.mjs`), at real size and in context.
- `overlaps.mjs`: nothing lifted off the phone without an opaque surface, no text over another
  text, no text resting over the phone.
- `purity.mjs`: `seek(t)` does not depend on the order frames are requested (renders in parallel
  segments rely on it).
- `errors.mjs`: the page throws no errors and logs no warnings during a full pass.
- Rolling digits checked frame by frame around every change: no garbage values in between.
- Lifted elements: crop and vector replica match (`compare.py`, `diffpng.py`).

## Render

- `jumps.py`: no frozen or skipped frames in the recorded material once placed in the film.
- `stutter.py`: no "two near-identical frames followed by a big jump" pattern.
- `diffs.py`, `edges.py`, `joins.py`: no unexpected cuts at segment joins.
- `ffprobe`: 1920x1080 or 1080x1920, 60 fps, H.264 yuv420p, AAC 48 kHz.

## Audio

- Integrated loudness -14 LUFS, true peak <= -1 dBTP (`ffmpeg -af loudnorm=print_format=summary`
  or `ebur128=peak=true`).
- `music_check.py`: no beat of the edit reaches 0.88 similarity with the vocal-chop fingerprint.
- Cuts on the beat, no clicks at the crossfades.
- Narrated cut: `transcribe.py` gives back the full script, the brand is recognized with and
  without a hint, `check_margin.py` shows no line where the music wins, `audio_artifacts.py` finds
  no clicks or abrupt cuts.

## Visual list

Must not appear anywhere: cursor, another app, debug or environment banners, a dirty status bar,
real personal data, clipped text, spelling mistakes or missing diacritics, maker branding on the
phone frame, a play glyph that is not in the brand.

## Machine care

Rendering, emulators and Whisper are heavy. Measure before each heavy batch and size parallelism
to what is free, not to what the machine has.

- `uptime`, `free -g`, and Windows free memory
  (`(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB`).
- Load average below about 60 % of the cores: up to 4 render processes. Between 60 % and 90 %: one
  at a time. Above 90 %: wait. (`video/scripts/resources.sh` turns free memory into a worker count
  and memory caps.)
- Windows never below 2 GB free while the emulator runs; WSL grows into Windows memory, so cap it
  in `.wslconfig` if needed.
- Run renders inside a memory-capped scope, so a runaway browser cannot take the machine down:
  `systemd-run --user --scope -p MemoryMax=10G -p MemorySwapMax=2G <command>`.
- One Gradle build at a time on the whole machine (`pgrep -f GradleDaemon`).
- Temperatures on long batches, especially in hot weather: `tools/windows/temperatures.ps1`
  (Core Temp for the CPU, LibreHardwareMonitor for an AMD GPU; change `GpuAmd` to `GpuNvidia`
  for NVIDIA). Pause above 85 C on the CPU or 80 C on the GPU.
- Never kill processes you did not start, and never touch emulators of other sessions.
