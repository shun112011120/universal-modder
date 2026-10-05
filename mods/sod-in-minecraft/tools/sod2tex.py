"""Decode SoD2's high-res texture mips (`*.hirez.ubulk`: raw BC1/DXT1 or BC3/DXT5, no header) to PNG.

UE Viewer's sod2 mode exports textures only up to the mips stored in the package; SoD2 streams the top mip
from a separate `.hirez.ubulk` in another pak. Those are bare block-compressed images, so the size gives the
format: w*h/2 bytes = BC1, w*h bytes = BC3 (square, power of two).

    python tools/sod2tex.py IN.hirez.ubulk OUT.png [--format bc1|bc3]
"""
import struct
import sys
import zlib
from pathlib import Path


def _565(c):
    return ((c >> 11) & 31) * 255 // 31, ((c >> 5) & 63) * 255 // 63, (c & 31) * 255 // 31


def _bc1_colors(c0, c1, has_alpha_mode):
    a, b = _565(c0), _565(c1)
    if c0 > c1 or not has_alpha_mode:
        return [a + (255,), b + (255,), tuple((2 * x + y) // 3 for x, y in zip(a, b)) + (255,),
                tuple((x + 2 * y) // 3 for x, y in zip(a, b)) + (255,)]
    return [a + (255,), b + (255,), tuple((x + y) // 2 for x, y in zip(a, b)) + (255,), (0, 0, 0, 0)]


def decode(data, w, h, fmt):
    px = bytearray(w * h * 4)
    step = 8 if fmt == "bc1" else 16
    i = 0
    for by in range(0, h, 4):
        for bx in range(0, w, 4):
            blk = data[i:i + step]
            i += step
            alpha = None
            if fmt == "bc3":
                a0, a1 = blk[0], blk[1]
                bits = int.from_bytes(blk[2:8], "little")
                pal = [a0, a1] + ([((6 - k) * a0 + k * a1) // 7 for k in range(1, 7)] if a0 > a1 else
                                  [((4 - k) * a0 + k * a1) // 5 for k in range(1, 5)] + [0, 255])
                alpha = [pal[(bits >> (3 * k)) & 7] for k in range(16)]
                blk = blk[8:]
            c0, c1, idx = struct.unpack("<HHI", blk)
            cols = _bc1_colors(c0, c1, fmt == "bc1")
            for k in range(16):
                x, y = bx + (k & 3), by + (k >> 2)
                r, g, b, a = cols[(idx >> (2 * k)) & 3]
                o = (y * w + x) * 4
                px[o:o + 4] = bytes((r, g, b, alpha[k] if alpha else a))
    return px


def write_png(path, px, w, h):
    raw = b"".join(b"\x00" + bytes(px[y * w * 4:(y + 1) * w * 4]) for y in range(h))

    def chunk(kind, d):
        return struct.pack(">I", len(d)) + kind + d + struct.pack(">I", zlib.crc32(kind + d) & 0xFFFFFFFF)

    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def main(argv):
    src, dst = Path(argv[0]), Path(argv[1])
    data = src.read_bytes()
    fmt = argv[argv.index("--format") + 1] if "--format" in argv else None
    for f in ([fmt] if fmt else ["bc1", "bc3"]):
        side = int(round((len(data) * (2 if f == "bc1" else 1)) ** 0.5))
        if side * side == len(data) * (2 if f == "bc1" else 1) and side & (side - 1) == 0:
            write_png(dst, decode(data, side, side, f), side, side)
            print(f"{dst.name}: {side}x{side} {f}")
            return
    sys.exit(f"{src.name}: {len(data)} bytes is not a square BC1/BC3 mip")


if __name__ == "__main__":
    main(sys.argv[1:])
