#!/usr/bin/env bash
# app_fps.sh "<shell actions on the emulator separated by ;>" label
# Measures with SurfaceFlinger timestats how the app presents its frames during the actions.
# PACKAGE=<app package> [SERIAL=emulator-NNNN] app_fps.sh "..." label
SERIAL=${SERIAL:-$(python3 /PATH/TO/WORKDIR/kitconfig.py emulator_serial)}
A="adb -s $SERIAL shell"
mkdir -p /PATH/TO/WORKDIR/tests60
timeout 30 $A "dumpsys SurfaceFlinger --timestats -disable -clear; dumpsys SurfaceFlinger --timestats -enable" >/dev/null
eval "$1"
timeout 30 $A "dumpsys SurfaceFlinger --timestats -dump" > /PATH/TO/WORKDIR/tests60/ts-$2.txt
timeout 30 $A "dumpsys SurfaceFlinger --timestats -disable" >/dev/null
python3 - /PATH/TO/WORKDIR/tests60/ts-$2.txt "$2" <<'PY'
import re,sys
t=open(sys.argv[1]).read()
for b in t.split("layerName = ")[1:]:
    if __import__("os").environ["PACKAGE"] not in b.splitlines()[0]: continue
    h=re.search(r"present2present histogram is as below:\n(.*)",b).group(1)
    p=[(int(k),int(v)) for k,v in re.findall(r"(\d+)ms=(\d+)",h)]
    mov=[(k,v) for k,v in p if k<100]
    n=sum(v for k,v in mov)
    print(f"{sys.argv[2]}: frames {re.search(r'totalFrames = (\d+)',b).group(1)}; intervals in motion {n}: <=20ms {sum(v for k,v in mov if k<=20)}, 21-35ms {sum(v for k,v in mov if 20<k<=35)}, 36-99ms {sum(v for k,v in mov if k>35)}; max {max([k for k,v in mov if v] or [0])} ms; pauses >=100ms {sum(v for k,v in p if k>=100)}")
PY
