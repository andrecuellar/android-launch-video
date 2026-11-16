"""Compares ink boxes between the crop panel (1) and the replica panel (2) of a calibration image
(two panels stacked vertically, e.g. calib-*.png).
Usage: compare.py <image.png> <panel_height> '{"name": [x0, y0, x1, y1, luma_threshold], ...}'
(panel_height = h + 40 + 4)"""
import subprocess, sys, json
import numpy as np
path, height = sys.argv[1], int(sys.argv[2])   # panel height (h + 40 + 4)
w,h = map(int, subprocess.run(["ffprobe","-v","error","-show_entries","stream=width,height","-of","csv=p=0",path],capture_output=True,text=True).stdout.strip().split(","))
img = np.frombuffer(subprocess.run(["ffmpeg","-loglevel","error","-i",path,"-f","rawvideo","-pix_fmt","rgb24","-"],capture_output=True,check=True).stdout,dtype=np.uint8).reshape(h,w,3).astype(int)
lum = img.mean(axis=2)
regions = json.loads(sys.argv[3])
for name, (x0,y0,x1,y1,u) in regions.items():
    out=[]
    for p in (0,1):
        sub = lum[p*height+y0:p*height+y1, x0:x1] < u
        ys,xs = np.nonzero(sub)
        out.append(None if len(ys)==0 else (xs.min()+x0, ys.min()+y0, xs.max()+x0, ys.max()+y0))
    a,b = out
    d = None if (a is None or b is None) else tuple(int(b[i]-a[i]) for i in range(4))
    print(f"{name:10s} crop {a}  replica {b}  delta {d}")
