#!/usr/bin/env bash
# screencap.sh <out.png>: screenshot of the emulator.
SERIAL=${SERIAL:-$(python3 /PATH/TO/WORKDIR/kitconfig.py emulator_serial)}
adb -s "$SERIAL" exec-out screencap -p > "$1"
