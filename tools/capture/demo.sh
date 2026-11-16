#!/usr/bin/env bash
# Clean status bar with the SystemUI demo mode: 9:41, full battery and wifi, no notifications.
# Undo with: adb -s <serial> shell am broadcast -a com.android.systemui.demo -e command exit
SERIAL=${SERIAL:-$(python3 /PATH/TO/WORKDIR/kitconfig.py emulator_serial)}
A="adb -s $SERIAL shell"
$A settings put global sysui_demo_allowed 1
b(){ $A am broadcast -a com.android.systemui.demo -e command "$@" >/dev/null; }
b enter
b clock -e hhmm 0941
b battery -e level 100 -e plugged false
b network -e wifi show -e level 4 -e fully true
b network -e mobile hide
b network -e airplane hide
b notifications -e visible false
b status -e volume hide -e bluetooth hide -e location hide -e alarm hide -e sync hide -e tty hide -e eri hide -e mute hide -e speakerphone hide
