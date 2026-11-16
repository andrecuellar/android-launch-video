# Real 60 fps capture

Everything that moves inside the phone in the film is this capture, so it has to be smooth.

## Why not screenrecord

`adb shell screenrecord` encodes inside the emulator and drops frames: about 41 unique frames per
second at 1080x2400 and 53 at 720x1600. Scrolls and sheets look choppy, and interpolation does not
fix it. `tools/capture/clip.py` (screenrecord) and `sync.py` stay for quick tests only.

## Option A: Windows host + GPU (tested)

Tested on Windows 11 with WSL2 and an AMD GPU (`hevc_amf`). NVIDIA (`h264_nvenc`, `hevc_nvenc`) is
wired in the config but untested. The toolkit runs in WSL and calls Windows executables through
WSL interop (`windows_exec_wrapper` in `config.json` if your setup needs a wrapper to run `.exe`
files reliably; empty runs them directly).

You need on Windows:

- The Android SDK emulator (`android_sdk_windows`).
- An ffmpeg build with `ddagrab` and your hardware encoder (for example the gyan.dev full build),
  path in `windows_ffmpeg_wsl`.
- A capture folder on a Windows disk (`capture_dir_windows` and its WSL path `capture_dir_wsl`):
  ffmpeg writes there and `capture.py` moves each clip to WSL.
- `tools/windows/display.ps1`, `window.ps1` and `temperatures.ps1` copied to `windows_tools_dir`.

### 1. Start the emulator on Windows, with the GPU

Portrait 1080x2400 AVD (`avd_name`). Emulator ports are global to the machine: pick a free one
(`adb devices`) and set `emulator_serial` to `emulator-<port>`.

```bash
PS=$(python3 kitconfig.py powershell_wsl)
cd /tmp; "$PS" -NoProfile -Command "Start-Process -FilePath 'C:\Android\Sdk\emulator\emulator.exe' -ArgumentList '-avd','<AVD>','-port','<PORT>','-no-snapshot-save','-no-boot-anim','-cores','8','-memory','4096','-gpu','host'"
```

`cd /tmp` avoids launching a Windows process with a WSL working directory. If adb in WSL cannot
see the Windows emulator, use the Windows `adb.exe` (APKs are then installed with a Windows path).

### 2. Rotate the monitor to portrait (ask first)

So the phone fits at 1:1. Only with the reviewer's OK, and always restore it, also on failure.

```bash
"$PS" -NoProfile -ExecutionPolicy Bypass -File 'C:\...\display.ps1' status    # saves original.json the first time
"$PS" -NoProfile -ExecutionPolicy Bypass -File 'C:\...\display.ps1' portrait  # add -Test to validate only
"$PS" -NoProfile -ExecutionPolicy Bypass -File 'C:\...\display.ps1' restore
```

### 3. Fix the emulator window and find the screen corner

`window.ps1 list | move X Y | place X Y W H | top | normal` lists the emulator windows with their
client area, moves the main one and keeps it on top. Desktop Duplication delivers the desktop
**unrotated** (for example 3440x1440 for a rotated ultrawide), so the phone screen is a
`capture_size` rectangle (2400x1080 for a 1080x2400 phone) at `screen_corner`, and
`capture_filter` rotates it with `transpose=1`.

Measure the corner with a test capture: `python3 capture/gpu_test.py rotate corner-01 [script.sh]`
records 20 s at the configured corner (optionally running a script that scrolls the app); look at
`tests60/corner-01.mp4` and adjust `screen_corner` until the phone screen fills the frame with no
desktop border.

### 4. Keep Windows unlocked and the screen on

With the lock screen up, Desktop Duplication gets no frames, and adb input does not count as user
activity. Turn off the screensaver, raise the screen timeout while recording and put it back at the
end:

```powershell
powercfg /change monitor-timeout-ac 120   # while recording
powercfg /change monitor-timeout-ac 5     # back to your usual value
if (Get-Process LogonUI -ErrorAction SilentlyContinue) {'locked'} else {'free'}
```

### 5. Record

```python
import sys; sys.path.insert(0, "/path/to/workdir/capture")
from capture import ClipGPU, wait
with ClipGPU("03-search-filter", max_seconds=40) as c:
    wait(1.0)
    c.tap(540, 1650)
    wait(1.2)
    c.swipe(540, 1800, 540, 700, 420)
    wait(1.5)
```

Each clip goes to `clips60/<name>.mp4` with `clips60/<name>.taps.json`
(`[{"t", "type": "tap"|"swipe", "x", "y", "x2", "y2", "ms"}]`). Encoding is almost lossless
(`hevc_amf -rc cqp -qp_i 12 -qp_p 14`, GOP 30). `ui.py tap <text>` finds a button by its text or
content description when you write the recording script.

### 6. Taps and sync

Taps and swipes go through `adb shell input`, with the emulator's `date +%s.%N` before and after.
The touch happens at the end of `input` (about 0.03 s before "after"); a swipe fills its last `ms`.
ffmpeg starts on Windows a while after the logged start, so `python3 capture/sync60.py <name>`
estimates the offset from the first action (preceded by stillness), refines it with the median over
all actions, subtracts the paint latency and rewrites the tap log in video time. The original
emulator-clock log is kept next to the tools.

### 7. Measure every clip

- `measure2.py clips60/<name>.mp4`: unique frames per second while there is motion, intervals over
  20 and 35 ms, hitches between motion runs. Target: 53 to 60 in the motion core.
- `video/scripts/stutter.py` and `jumps.py` on the material (see `references/film.md`).
- `PACKAGE=<app.package> capture/app_fps.sh "<adb actions>" label`: SurfaceFlinger timestats of
  the app layer, to tell whether the app itself draws at 60 inside the emulator.
- `sf_latency.py`: presentation intervals of the app layer right after a swipe.

A clip with stutter is recorded again. It is not fixed by interpolation.

### 8. Windows memory

Keep at least 2 GB free on Windows while the emulator runs:
`(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB`.

## Option B: physical phone with scrcpy (UNTESTED)

`scrcpy --no-audio --max-fps 60 --record=clip.mkv` on a 60 Hz or faster phone records the real
device. Not tested with this toolkit: the tap log (`ClipGPU`) and `sync60.py` assume the emulator
clock and the Windows capture folder, so they would need adapting (log `adb shell date` the same
way and point `VID` at the scrcpy output). Disable "show touches" on the device: the film draws its
own touch indicators.

## Option C: macOS / Linux hosts

Not covered. Any capture that delivers 60 unique frames per second of the phone screen works if
you produce the same `<name>.mp4` plus `<name>.taps.json` pair.
