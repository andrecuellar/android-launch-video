"""Records a clip with the host GPU (ffmpeg ddagrab + a hardware encoder) and logs every tap and swipe.

ffmpeg runs on Windows and writes to a Windows folder; when the clip ends it is moved to WSL and
removed from Windows. Action times come from the emulator clock, as in clip.py; the offset against
the video is corrected afterwards by sync60.py, from the visual change each action causes.

Machine values (ffmpeg.exe, capture folders, encoder, emulator serial) come from config.json.

Use as a module:
    import sys; sys.path.insert(0, "/PATH/TO/WORKDIR/capture")
    from capture import ClipGPU, wait, configure
    configure(x, y)          # corner of the phone screen on the (unrotated) desktop
    with ClipGPU("01-home-buy", max_seconds=40) as c: ...
"""
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, "/PATH/TO/WORKDIR")
from kitconfig import cfg, windows_command  # noqa: E402

A = ["adb", "-s", cfg("emulator_serial")]
FFMPEG = cfg("windows_ffmpeg_wsl")
CAPTURE_DIR = cfg("capture_dir_wsl")
CAPTURE_DIR_WIN = cfg("capture_dir_windows")
VID = "/PATH/TO/WORKDIR/clips60"
TOOLS = "/PATH/TO/WORKDIR/capture"
INPUT_TAIL = 0.03
ORIGIN = {"x": cfg("screen_corner")[0], "y": cfg("screen_corner")[1]}

# Encoder settings that keep the capture almost lossless. hevc_amf is the tested one (AMD);
# the NVENC entries are untested. Set "encoder_args" in config.json to override.
ENCODER_DEFAULTS = {
    "hevc_amf": ["-quality", "quality", "-rc", "cqp", "-qp_i", "12", "-qp_p", "14"],
    "h264_amf": ["-quality", "quality", "-rc", "cqp", "-qp_i", "12", "-qp_p", "14"],
    "hevc_nvenc": ["-preset", "p7", "-rc", "constqp", "-qp", "14"],
    "h264_nvenc": ["-preset", "p7", "-rc", "constqp", "-qp", "14"],
}


def encoder_args():
    encoder = cfg("encoder")
    extra = cfg("encoder_args") or ENCODER_DEFAULTS.get(encoder)
    if extra is None:
        raise SystemExit(f"no default settings for encoder {encoder}: set encoder_args in config.json")
    return ["-c:v", encoder, *extra, "-g", "30"]


def configure(x, y):
    ORIGIN["x"], ORIGIN["y"] = x, y


def sh(cmd):
    return subprocess.run(A + ["shell", cmd], capture_output=True, text=True, timeout=120).stdout


def wait(seconds):
    time.sleep(seconds)


def ffmpeg_args(dest_win, max_seconds):
    # The monitor is rotated: ddagrab delivers the desktop unrotated (for example 3440x1440), so
    # the phone window is cropped in those coordinates (capture_size, e.g. 2400x1080) and the
    # capture_filter rotates it 90 degrees to 1080x2400.
    w, h = cfg("capture_size")
    source = (f"ddagrab=output_idx=0:framerate=60:draw_mouse=0:"
              f"offset_x={ORIGIN['x']}:offset_y={ORIGIN['y']}:video_size={w}x{h}")
    return [FFMPEG, "-hide_banner", "-loglevel", "warning", "-y", "-f", "lavfi", "-i", source,
            "-t", str(max_seconds), "-vf", cfg("capture_filter"),
            *encoder_args(), dest_win]


class ClipGPU:
    def __init__(self, name, max_seconds=60):
        self.name = name
        self.max_seconds = max_seconds
        self.ev = []
        self.raw = []
        self.t0 = None

    def __enter__(self):
        os.makedirs(VID, exist_ok=True)
        os.makedirs(CAPTURE_DIR, exist_ok=True)
        dest_win = CAPTURE_DIR_WIN + "\\" + self.name + ".mp4"
        self.dest_c = f"{CAPTURE_DIR}/{self.name}.mp4"
        if os.path.exists(self.dest_c):
            os.remove(self.dest_c)
        # The emulator clock right before launching ffmpeg: sync60.py measures the real offset.
        self.t0 = float(sh("date +%s.%N").strip())
        args = ffmpeg_args(dest_win, self.max_seconds)
        self.p = subprocess.Popen(windows_command(args[0], *args[1:]),
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, cwd="/tmp")
        time.sleep(1.2)
        if self.p.poll() is not None:
            raise SystemExit(f"ffmpeg exited at start: {self.p.stdout.read().decode(errors='replace')}")
        return self

    def _input(self, args):
        out = sh(f"a=$(date +%s.%N); input {args}; b=$(date +%s.%N); echo $a $b").split()
        return float(out[-2]), float(out[-1])

    def tap(self, x, y):
        a, b = self._input(f"tap {x} {y}")
        self.ev.append({"t": round(b - INPUT_TAIL - self.t0, 3), "type": "tap",
                        "x": x, "y": y, "x2": x, "y2": y, "ms": 100})
        self.raw.append({"action": "tap", "before": round(a - self.t0, 3), "after": round(b - self.t0, 3)})

    def swipe(self, x, y, x2, y2, ms):
        a, b = self._input(f"swipe {x} {y} {x2} {y2} {ms}")
        self.ev.append({"t": round(b - ms / 1000 - INPUT_TAIL - self.t0, 3), "type": "swipe",
                        "x": x, "y": y, "x2": x2, "y2": y2, "ms": ms})
        self.raw.append({"action": "swipe", "before": round(a - self.t0, 3), "after": round(b - self.t0, 3)})

    def key(self, code):
        sh(f"input keyevent {code}")

    def text(self, text):
        sh(f"input text '{text}'")

    def __exit__(self, *exc):
        try:
            self.p.stdin.write(b"q")
            self.p.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        try:
            output, _ = self.p.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            self.p.kill()
            output = b""
        time.sleep(1.0)
        dest = f"{VID}/{self.name}.mp4"
        shutil.move(self.dest_c, dest)
        with open(f"{VID}/{self.name}.taps.json", "w") as f:
            json.dump(self.ev, f, ensure_ascii=False, indent=1)
        with open(f"{TOOLS}/{self.name}.gpu-raw.json", "w") as f:
            json.dump(self.raw, f, indent=1)
        warning = output.decode(errors="replace").strip()
        print("clip", dest, os.path.getsize(dest), "bytes,", len(self.ev), "actions",
              ("| ffmpeg: " + warning[-300:]) if warning else "")
        return False
