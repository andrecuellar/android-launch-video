"""Records a clip with screenrecord and logs every tap and swipe. For tests only: screenrecord
does not reach 60 fps (about 41 fps at 1080x2400). Use capture.py for the real takes.

Times come from the emulator clock (date +%s.%N), not the host's: the start is taken right before
launching screenrecord, and each action right before and right after `input`. The real touch
happens at the end of `input` (the command's Java VM starts first), so:
- tap: t = after - 0.03 s;
- swipe: t = after - ms - 0.03 s (the gesture fills the last `ms` milliseconds).

Use as a module:
    import sys; sys.path.insert(0, "/PATH/TO/WORKDIR/capture")
    from clip import Clip, wait
    with Clip("01-home") as c: c.tap(540, 1200); wait(1)
"""
import json
import os
import subprocess
import sys
import threading
import time

sys.path.insert(0, "/PATH/TO/WORKDIR")
from kitconfig import cfg  # noqa: E402

A = ["adb", "-s", cfg("emulator_serial")]
VID = "/PATH/TO/WORKDIR/clips"
INPUT_TAIL = 0.03


def sh(cmd):
    return subprocess.run(A + ["shell", cmd], capture_output=True, text=True, timeout=120).stdout


def wait(seconds):
    time.sleep(seconds)


class Clip:
    def __init__(self, name):
        self.name = name
        self.ev = []
        self.raw = []
        self.t0 = None

    def __enter__(self):
        sh(f"rm -f /sdcard/{self.name}.mp4")
        self.p = subprocess.Popen(
            A + ["shell", f"echo START $(date +%s.%N); exec screenrecord --bit-rate 20000000 /sdcard/{self.name}.mp4"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        line = self.p.stdout.readline().strip()
        if not line.startswith("START"):
            raise SystemExit(f"screenrecord did not start: {line!r}")
        self.t0 = float(line.split()[1])
        self.output = []
        threading.Thread(target=lambda: self.output.extend(self.p.stdout), daemon=True).start()
        time.sleep(1.5)
        return self

    def _input(self, args):
        out = sh(f"a=$(date +%s.%N); input {args}; b=$(date +%s.%N); echo $a $b").split()
        return float(out[-2]), float(out[-1])

    def tap(self, x, y):
        a, b = self._input(f"tap {x} {y}")
        t = round(b - INPUT_TAIL - self.t0, 3)
        self.ev.append({"t": t, "type": "tap", "x": x, "y": y, "x2": x, "y2": y, "ms": 100})
        self.raw.append({"action": "tap", "before": round(a - self.t0, 3), "after": round(b - self.t0, 3)})

    def swipe(self, x, y, x2, y2, ms):
        a, b = self._input(f"swipe {x} {y} {x2} {y2} {ms}")
        t = round(b - ms / 1000 - INPUT_TAIL - self.t0, 3)
        self.ev.append({"t": t, "type": "swipe", "x": x, "y": y, "x2": x2, "y2": y2, "ms": ms})
        self.raw.append({"action": "swipe", "before": round(a - self.t0, 3), "after": round(b - self.t0, 3)})

    def __exit__(self, *exc):
        time.sleep(0.2)
        sh("pkill -INT screenrecord")
        try:
            self.p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.p.kill()
        time.sleep(1.5)
        dest = f"{VID}/{self.name}.mp4"
        with open(dest, "wb") as f:
            subprocess.run(A + ["exec-out", f"cat /sdcard/{self.name}.mp4"], stdout=f, timeout=300)
        sh(f"rm -f /sdcard/{self.name}.mp4")
        with open(f"{VID}/{self.name}.taps.json", "w") as f:
            json.dump(self.ev, f, ensure_ascii=False, indent=1)
        with open(f"/PATH/TO/WORKDIR/capture/{self.name}.raw.json", "w") as f:
            json.dump(self.raw, f, indent=1)
        print("clip", dest, os.path.getsize(dest), "bytes,", len(self.ev), "actions")
        return False
