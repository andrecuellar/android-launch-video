"""PNG for Google Play: flattens to 8-bit-per-channel RGB (24 bits, no alpha) with ffmpeg and tags the
file as sRGB (sRGB, gAMA and cHRM chunks right after IHDR; any previous iCCP, sRGB, gAMA and cHRM are
removed). It also measures a PNG: size, color type, depth, whether it has alpha and whether it is
tagged sRGB.

Usage: png_srgb.py flatten <input.png> <output.png>
       png_srgb.py measure <file.png> [...]
"""
import os
import struct
import subprocess
import sys
import zlib


def chunks(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    i, out = 8, []
    while i < len(data):
        n = struct.unpack(">I", data[i:i + 4])[0]
        kind = data[i + 4:i + 8]
        out.append((kind, data[i + 8:i + 8 + n]))
        i += 12 + n
    return out


def chunk(kind, content):
    return struct.pack(">I", len(content)) + kind + content + struct.pack(">I", zlib.crc32(kind + content) & 0xFFFFFFFF)


def flatten(src, dst):
    tmp = dst + ".tmp.png"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-vf", "format=rgb24", "-pix_fmt", "rgb24", "-compression_level", "9", tmp], check=True)
    ch = [(t, c) for t, c in chunks(open(tmp, "rb").read()) if t not in (b"iCCP", b"sRGB", b"gAMA", b"cHRM", b"tEXt", b"zTXt", b"iTXt", b"tIME")]
    ihdr = ch[0]
    extra = [(b"sRGB", bytes([0])), (b"gAMA", struct.pack(">I", 45455)),
             (b"cHRM", struct.pack(">8I", 31270, 32900, 64000, 33000, 30000, 60000, 15000, 6000))]
    with open(dst, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        for t, c in [ihdr] + extra + ch[1:]:
            f.write(chunk(t, c))
    os.remove(tmp)


def measure(path):
    ch = chunks(open(path, "rb").read())
    w, h, depth, color = struct.unpack(">IIBB", ch[0][1][:10])
    names = {0: "gray", 2: "RGB", 3: "palette", 4: "gray with alpha", 6: "RGBA"}
    kinds = [t.decode() for t, _ in ch]
    alpha = color in (4, 6) or "tRNS" in kinds
    return {"file": os.path.basename(path), "width": w, "height": h, "color": names.get(color, color), "bits_per_channel": depth,
            "bits_per_pixel": depth * {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color], "alpha": alpha, "srgb": "sRGB" in kinds and "iCCP" not in kinds,
            "bytes": os.path.getsize(path)}


if __name__ == "__main__":
    if sys.argv[1] == "flatten":
        flatten(sys.argv[2], sys.argv[3])
    else:
        for r in sys.argv[2:]:
            print(measure(r))
