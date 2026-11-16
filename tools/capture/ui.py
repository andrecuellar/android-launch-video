#!/usr/bin/env python3
"""Screen hierarchy and tap by text (uiautomator).

Usage: ui.py dump | tap <text> [n] | find <text> [n]"""
import subprocess,sys,re,xml.etree.ElementTree as ET
sys.path.insert(0, "/PATH/TO/WORKDIR")
from kitconfig import cfg  # noqa: E402
A=["adb","-s",cfg("emulator_serial")]
def dump():
    subprocess.run(A+["shell","rm","-f","/sdcard/ui.xml"])
    o=subprocess.run(A+["shell","uiautomator","dump","/sdcard/ui.xml"],capture_output=True,text=True).stdout
    if "dumped" not in o: print("DUMP FAILED:",o); sys.exit(2)
    x=subprocess.run(A+["exec-out","cat","/sdcard/ui.xml"],capture_output=True,text=True).stdout
    return ET.fromstring(x[x.index("<"):])
def nodes(r):
    for n in r.iter("node"):
        t=(n.get("text") or "")+"|"+(n.get("content-desc") or "")
        b=list(map(int,re.findall(r"\d+",n.get("bounds"))))
        yield t,b,n
cmd=sys.argv[1]
r=dump()
if cmd=="dump":
    for t,b,n in nodes(r):
        if t!="|": print(b,repr(t.replace("\n"," / "))[:160], "clickable" if n.get("clickable")=="true" else "")
else:
    q=sys.argv[2].lower(); i=int(sys.argv[3]) if len(sys.argv)>3 else 0
    m=[(t,b) for t,b,n in nodes(r) if q in t.lower()]
    if not m: print("NOT FOUND",q); sys.exit(1)
    t,b=m[i]; x=(b[0]+b[2])//2; y=(b[1]+b[3])//2
    print("->",repr(t)[:80],x,y)
    if cmd=="tap": subprocess.run(A+["shell","input","tap",str(x),str(y)])
