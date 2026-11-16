"""Key without the lows: chroma from 160 to 1600 Hz per section, with Krumhansl profiles.
The sections (start, end, name) are example values from a past production: set them from your track.
Usage: key_detect.py <audio>"""
import subprocess, sys
import numpy as np
SR = 48000
x = np.frombuffer(subprocess.run(["ffmpeg","-loglevel","error","-i",sys.argv[1],"-ac","1","-ar",str(SR),"-f","f32le","-"],capture_output=True,check=True).stdout,dtype=np.float32)
names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
major = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
minor = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
def chroma(a, z, lo=160, hi=1600):
    seg = x[int(a*SR):int(z*SR)]; n=16384; hop=2048; w=np.hanning(n)
    f = np.fft.rfftfreq(n,1/SR); v=(f>lo)&(f<hi)
    note = (np.round(12*np.log2(f[v]/440.0)).astype(int)+9) % 12
    c = np.zeros(12)
    for i in range(0,len(seg)-n,hop):
        m = np.abs(np.fft.rfft(seg[i:i+n]*w))[v]
        np.add.at(c, note, m)
    return c/c.max()
for (a,z,name) in [(0,12,"intro 0-12"),(12.13,16.13,"build"),(16.13,32.13,"drop"),(32.13,48.13,"section 2"),(88.13,96.13,"ending"),(96.13,99,"tail")]:
    c = chroma(a,z)
    cand = sorted([(np.corrcoef(c,np.roll(major,r))[0,1],names[r]+" major") for r in range(12)]+[(np.corrcoef(c,np.roll(minor,r))[0,1],names[r]+" minor") for r in range(12)],reverse=True)[:3]
    order = " ".join(f"{names[i]}:{c[i]:.2f}" for i in np.argsort(-c)[:8])
    print(f"{name:12s} {order}\n             -> " + ", ".join(f"{n} {v:.2f}" for v,n in cand))
