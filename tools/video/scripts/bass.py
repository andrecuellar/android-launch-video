"""Dominant notes of the bass and of the harmony per bar, with long windows.
The phase (0.13036 s), the 2 s bar and the bar list are example values from a past production: set them from your
track (scripts/grid.py).
Usage: bass.py <audio>"""
import subprocess, sys
import numpy as np
SR = 48000
x = np.frombuffer(subprocess.run(["ffmpeg","-loglevel","error","-i",sys.argv[1],"-ac","1","-ar",str(SR),"-f","f32le","-"],capture_output=True,check=True).stdout,dtype=np.float32)
names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
def note(f):
    m = 69 + 12*np.log2(f/440.0); return names[int(round(m))%12] + str(int(round(m))//12 - 1), m - round(m)
def peaks(a, z, lo, hi, k=4):
    seg = x[int(a*SR):int(z*SR)]
    n = 1<<int(np.ceil(np.log2(len(seg))))
    spec = np.abs(np.fft.rfft(seg*np.hanning(len(seg)), n))
    f = np.fft.rfftfreq(n, 1/SR); v = (f>lo)&(f<hi)
    ff, ee = f[v], spec[v]
    out=[]; ee=ee.copy()
    for _ in range(k):
        i = int(np.argmax(ee)); out.append(ff[i])
        ee[max(0,i-int(len(ee)*0.01)):i+int(len(ee)*0.01)] = 0
    return out
phase=0.13036
for b in [6,7,8,9,10,11,12,13,14,15,44,45,46,47,48]:
    a = phase + 2*b; z = a+2
    bass = peaks(a+0.05, z, 35, 140, 3)
    mid = peaks(a+0.05, z, 140, 900, 5)
    print(f"bar {a:6.2f}: bass " + ", ".join(f"{note(f)[0]}({f:.1f})" for f in bass) + " | mids " + ", ".join(note(f)[0] for f in mid))
