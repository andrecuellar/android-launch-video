"""Test capture to find the corner of the phone screen on the desktop.

Records 20 s with ddagrab at the configured screen_corner and capture_size, rotated in the same
ffmpeg ("rotate") or as delivered ("native"), while an optional shell script moves the app (for
example a few `adb shell input swipe` calls). Look at the result and adjust screen_corner until
the phone screen fills the frame exactly, with no desktop border.

Usage: python3 gpu_test.py <rotate|native> <name> [script-that-moves-the-app.sh]
Writes /PATH/TO/WORKDIR/tests60/<name>.mp4
"""
import os, subprocess, sys, time, shutil
sys.path.insert(0, "/PATH/TO/WORKDIR")
sys.path.insert(0, "/PATH/TO/WORKDIR/capture")
from kitconfig import cfg, windows_command  # noqa: E402
from capture import encoder_args  # noqa: E402
mode = sys.argv[1]           # "rotate" (rotates in the same ffmpeg) or "native" (no rotation)
name = sys.argv[2]
mover = sys.argv[3] if len(sys.argv) > 3 else None
x, y = cfg("screen_corner")
w, h = cfg("capture_size")
src = f"ddagrab=framerate=60:draw_mouse=0:offset_x={x}:offset_y={y}:video_size={w}x{h}"
enc = encoder_args()
vf = ["-vf", cfg("capture_filter")] if mode == "rotate" else []
dest = cfg("capture_dir_windows") + "\\" + f"{name}.mp4"
cmd = windows_command(cfg("windows_ffmpeg_wsl"), "-hide_banner", "-loglevel", "warning",
                      "-y", "-f", "lavfi", "-i", src, *vf, *enc, "-t", "20", dest)
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd="/tmp")
time.sleep(2.5)
if mover:
    subprocess.run([mover])
else:
    time.sleep(5)
p.stdin.write(b"q"); p.stdin.flush()
out, _ = p.communicate(timeout=60)
print(out.decode(errors="replace")[-500:])
time.sleep(1)
os.makedirs("/PATH/TO/WORKDIR/tests60", exist_ok=True)
shutil.move(f"{cfg('capture_dir_wsl')}/{name}.mp4",
            f"/PATH/TO/WORKDIR/tests60/{name}.mp4")
