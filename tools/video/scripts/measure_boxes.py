"""Measures boxes and colors in a 1080x2400 screenshot (no PIL: reads through ffmpeg).
Usage: measure_boxes.py <image> color x,y ...
       measure_boxes.py <image> box x0,y0,x1,y1 #RRGGBB tolerance
       measure_boxes.py <image> ink x0,y0,x1,y1 luma_threshold
       measure_boxes.py <image> rows x y0,y1
       measure_boxes.py <image> columns y x0,x1
"""
import subprocess, sys, json
import numpy as np
def read(path):
    w,h=1080,2400
    raw=subprocess.run(["ffmpeg","-loglevel","error","-i",path,"-f","rawvideo","-pix_fmt","rgb24","-"],capture_output=True,check=True).stdout
    return np.frombuffer(raw,dtype=np.uint8).reshape(h,w,3).astype(int)
def box(m):
    ys,xs=np.nonzero(m)
    if len(ys)==0: return None
    return [int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())]
def hexa(c): return "#%02X%02X%02X"%tuple(int(v) for v in c)
img=read(sys.argv[1])
mode=sys.argv[2]
if mode=="color":
    for p in sys.argv[3:]:
        x,y=map(int,p.split(",")); print(p, hexa(img[y,x]))
elif mode=="box":
    # box of the pixels close to a color inside a region: box x0,y0,x1,y1 #RRGGBB tolerance
    x0,y0,x1,y1=map(int,sys.argv[3].split(",")); c=sys.argv[4]; tol=int(sys.argv[5])
    rgb=np.array([int(c[i:i+2],16) for i in (1,3,5)])
    sub=img[y0:y1,x0:x1]; m=(np.abs(sub-rgb).max(axis=2)<=tol)
    b=box(m); print("box", [b[0]+x0,b[1]+y0,b[2]+x0,b[3]+y0] if b else None, "px", int(m.sum()))
elif mode=="ink":
    # box of dark ink (luma < threshold) in a region
    x0,y0,x1,y1=map(int,sys.argv[3].split(",")); u=int(sys.argv[4])
    sub=img[y0:y1,x0:x1]; lum=sub.mean(axis=2); m=lum<u
    b=box(m); print("ink", [b[0]+x0,b[1]+y0,b[2]+x0,b[3]+y0] if b else None)
elif mode=="rows":
    # vertical profile: rows where the background color changes in column x
    x=int(sys.argv[3]); y0,y1=map(int,sys.argv[4].split(","))
    prev=None
    for y in range(y0,y1):
        c=hexa(img[y,x])
        if c!=prev: print(y,c); prev=c
elif mode=="columns":
    y=int(sys.argv[3]); x0,x1=map(int,sys.argv[4].split(","))
    prev=None
    for x in range(x0,x1):
        c=hexa(img[y,x])
        if c!=prev: print(x,c); prev=c
