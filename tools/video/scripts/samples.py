"""Prints a grid of color samples (RRGGBB, or ---- where alpha < 140) of a 1536x1024 RGBA image.
Usage: samples.py image.png
The rows and columns sampled are example values from a past production: adapt them."""
import subprocess, sys
import numpy as np
W,H=1536,1024
raw=subprocess.run(["ffmpeg","-loglevel","error","-i",sys.argv[1],"-f","rawvideo","-pix_fmt","rgba","-"],capture_output=True,check=True).stdout
img=np.frombuffer(raw,dtype=np.uint8).reshape(H,W,4)
for row in [260,280,300,320,340,380,420,460,490,510,530,550]:
    out=[]
    for x in range(540,1001,30):
        p=img[row,x]
        out.append("  ----  " if p[3]<140 else "%02X%02X%02X"%tuple(p[:3]))
    print(row, " ".join(out))
