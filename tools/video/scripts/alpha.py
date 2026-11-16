"""Box of the opaque pixels (alpha > 140) of each image. Usage: alpha.py image.png ..."""
import subprocess, sys
import numpy as np
for path in sys.argv[1:]:
    w,h = map(int, subprocess.run(["ffprobe","-v","error","-show_entries","stream=width,height","-of","csv=p=0",path],capture_output=True,text=True).stdout.strip().split(","))
    raw=subprocess.run(["ffmpeg","-loglevel","error","-i",path,"-f","rawvideo","-pix_fmt","rgba","-"],capture_output=True,check=True).stdout
    a=np.frombuffer(raw,dtype=np.uint8).reshape(h,w,4)[...,3]
    ys,xs=np.nonzero(a>140); print(path.split("/")[-1], w, h, "alpha box", xs.min(), ys.min(), xs.max(), ys.max())
