#!/usr/bin/env bash
# Prints how many render browsers are allowed right now and why.
# Rules: while clips are being recorded (emulator in use) or a build is running, 2 at most;
# otherwise up to 8. If Windows has less than 2 GB free or WSL less than 5 GB available, 0.
# The end of the recording is signaled by creating the file video/scripts/RECORDING_DONE.
DIR=$(dirname "$(readlink -f "$0")")   # before the cd: with a relative path, $0 resolves from here
WRAP=$(python3 /PATH/TO/WORKDIR/kitconfig.py windows_exec_wrapper)
PS=$(python3 /PATH/TO/WORKDIR/kitconfig.py powershell_wsl)
cd /tmp || exit 1
win_gb=$($WRAP "$PS" -NoProfile -Command "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB" 2>/dev/null | tr -d '\r' | tail -1)
wsl_mb=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
building=$(pgrep -f "[f]lutter build|[g]radlew " | wc -l)
if [ -f "$DIR/RECORDING_DONE" ]; then recording=0; else recording=1; fi
cap=8
[ "$recording" = 1 ] && cap=2
[ "$building" -gt 0 ] && cap=2
ok_win=$(awk -v g="${win_gb:-0}" 'BEGIN{print (g>=2.0)?1:0}')
[ "$ok_win" = 0 ] && cap=0
[ "$wsl_mb" -lt 5120 ] && cap=0
memmax=10G; swapmax=2G
[ "$cap" -le 2 ] && { memmax=6G; swapmax=1G; }
echo "workers=$cap memmax=$memmax swapmax=$swapmax windows_gb=${win_gb:-?} wsl_mb=$wsl_mb building=$building recording=$recording"
