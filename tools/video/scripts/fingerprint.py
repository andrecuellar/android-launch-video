"""Spectral fingerprint of an unwanted hit (for example a hit shaped like a voice) and its similarity in any audio.

Fingerprint: beats 2 to 4 of the reference bar of the track (bar 94.13 here; an example value from a past
production: set it to a bar of your track that carries the unwanted layer). Per window: 40 log bands from 250 Hz
to 6 kHz, energy in dB, centered (the mean is subtracted) and cosine similarity with the fingerprint.

Usage as a module: from fingerprint import Fingerprint; h = Fingerprint(track, variant); h.similarity(x, t)
"""
import subprocess
import numpy as np

SR = 48000
P = 0.49999948887468326  # beat period of the example track (120 BPM, measured with scripts/grid.py)


def read_mono(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


class Fingerprint:
    def __init__(self, track, length=0.120, centered=False, hann=False, total=False, template="hits", offset=0.0):
        self.length, self.centered, self.hann, self.total = length, centered, hann, total
        self.n = int(round(length * SR))
        self.edges = np.geomspace(250, 6000, 41)
        f = np.fft.rfftfreq(self.n, 1 / SR)
        self.idx = [np.where((f >= self.edges[i]) & (f < self.edges[i + 1]))[0] for i in range(40)]
        self.w = np.hanning(self.n) if hann else np.ones(self.n)
        lines = [94.1303 + k * P for k in (1, 2, 3)]
        times = [l + offset for l in lines]
        vecs = [self.vector(track, t) for t in times]
        self.ref = self._norm(np.mean(vecs, axis=0)) if template == "hits" else None

    def _norm(self, v):
        v = v - v.mean()
        return v / (np.linalg.norm(v) + 1e-12)

    def vector(self, x, t):
        i0 = int(round((t - (self.length / 2 if self.centered else 0)) * SR))
        seg = x[max(0, i0):max(0, i0) + self.n]
        if len(seg) < self.n: seg = np.pad(seg, (0, self.n - len(seg)))
        e = np.abs(np.fft.rfft(seg * self.w)) ** 2
        b = np.array([(e[ix].sum() if self.total else e[ix].mean()) if len(ix) else 1e-20 for ix in self.idx])
        return self._norm(10 * np.log10(b + 1e-20))

    def similarity(self, x, t):
        return float(np.dot(self.vector(x, t), self.ref))
