"""Read State of Decay 2's .pak files (Xbox app install) on the owner's own PC.

SoD2 uses a custom pak version (0x10003: a UE 4.x v3 pak with a flag in the high word), which UE Viewer doesn't
mount. The index is plain (not encrypted). This reader lists and extracts entries; whatever it extracts goes
into a folder the caller names, which must be outside the repo (e.g. `My Mods/sod2-extract`): SoD2's files are
for the owner's own game, never committed or shared.

    python tools/sod2pak.py list [PATTERN]              # every packed file whose path matches PATTERN (regex)
    python tools/sod2pak.py extract PATTERN OUTDIR      # extract matching files (uasset/uexp/ubulk...)
    python tools/sod2pak.py probe PATH                  # header bytes of one entry's blocks (format research)
"""
import os
import re
import struct
import sys
import zlib
from pathlib import Path

PAKS = Path(os.environ.get("SOD2_PAKS", r"C:\XboxGames\State of Decay 2\Content\StateOfDecay2\Content\Paks"))
MAGIC = 0x5A6F12E1


class Entry:
    __slots__ = ("pak", "name", "offset", "size", "usize", "method", "blocks", "encrypted", "block_size")


def _fstring(b, i):
    n = struct.unpack_from("<i", b, i)[0]
    i += 4
    if n == 0:
        return "", i
    if n < 0:  # UTF-16
        s = b[i:i - 2 * n].decode("utf-16-le").rstrip("\x00")
        return s, i - 2 * n
    return b[i:i + n].decode("utf-8", "replace").rstrip("\x00"), i + n


def read_index(pak):
    size = pak.stat().st_size
    with open(pak, "rb") as f:
        f.seek(size - 44)
        magic, version, off, isz = struct.unpack("<IiQQ", f.read(24))
        if magic != MAGIC:
            raise ValueError(f"{pak.name}: no pak footer")
        f.seek(off)
        b = f.read(isz)
    mount, i = _fstring(b, 0)
    count = struct.unpack_from("<i", b, i)[0]
    i += 4
    out = []
    for _ in range(count):
        e = Entry()
        e.pak = pak
        name, i = _fstring(b, i)
        e.name = mount.replace("../../../", "") + name
        e.offset, e.size, e.usize, e.method = struct.unpack_from("<qqqi", b, i)
        i += 28 + 20  # + sha1
        e.blocks = []
        if e.method != 0:
            nb = struct.unpack_from("<i", b, i)[0]
            i += 4
            for _ in range(nb):
                e.blocks.append(struct.unpack_from("<qq", b, i))
                i += 16
        e.encrypted, e.block_size = struct.unpack_from("<BI", b, i)
        i += 5
        out.append(e)
    return version, out


def all_entries():
    for pak in sorted(PAKS.glob("*.pak")):
        _, entries = read_index(pak)
        yield from entries


def lz4_block(src, limit):
    """Decode one raw LZ4 block (no frame header) of at most `limit` bytes."""
    out = bytearray()
    i, n = 0, len(src)
    while i < n:
        token = src[i]
        i += 1
        lit = token >> 4
        if lit == 15:
            while True:
                b = src[i]
                i += 1
                lit += b
                if b != 255:
                    break
        out += src[i:i + lit]
        i += lit
        if i >= n or len(out) >= limit:
            break
        off = src[i] | (src[i + 1] << 8)
        i += 2
        ml = token & 15
        if ml == 15:
            while True:
                b = src[i]
                i += 1
                ml += b
                if b != 255:
                    break
        ml += 4
        start = len(out) - off
        if off >= ml:
            out += out[start:start + ml]
        else:  # overlapping copy: repeat the last `off` bytes
            for k in range(ml):
                out.append(out[start + k])
    return bytes(out)


def _decompress(method, data, usize):
    """SoD2: 0x103 = raw LZ4 blocks (Undead Labs' own compression plugin); 1 = zlib."""
    if method == 0x103:
        return lz4_block(data, usize)
    if method & 0xFF == 1:
        return zlib.decompress(data)
    raise NotImplementedError(f"compression method 0x{method:x}")


def read_entry(e):
    # an entry's data starts with a copy of its own header; block offsets are relative to the entry (UE >= 4.20)
    # or absolute (older): try both
    with open(e.pak, "rb") as f:
        if e.method == 0:
            f.seek(e.offset)
            head = f.read(e.size + 128)
            return head[-e.size:] if len(head) >= e.size else head  # header length varies; callers check magic
        parts = []
        left = e.usize
        for start, end in e.blocks:
            absolute = start if start >= e.offset else e.offset + start
            f.seek(absolute)
            part = _decompress(e.method, f.read(end - start), min(e.block_size, left))
            parts.append(part)
            left -= len(part)
        data = b"".join(parts)
        if len(data) != e.usize:
            raise ValueError(f"{e.name}: got {len(data)} bytes, expected {e.usize}")
        return data


def main(argv):
    cmd = argv[0] if argv else "list"
    if cmd == "list":
        pat = re.compile(argv[1] if len(argv) > 1 else ".", re.I)
        n = 0
        for e in all_entries():
            if pat.search(e.name):
                print(f"{e.usize:>10}  m=0x{e.method:x}  {e.pak.name[9:15]}  {e.name}")
                n += 1
        print(n, "files", file=sys.stderr)
    elif cmd == "probe":
        for e in all_entries():
            if e.name == argv[1]:
                print(vars_of(e))
                with open(e.pak, "rb") as f:
                    for start, end in e.blocks[:2]:
                        for label, pos in (("abs", start), ("rel", e.offset + start)):
                            f.seek(pos)
                            print(label, pos, f.read(16).hex())
                return
        print("not found")
    elif cmd == "extract":
        pat, out = re.compile(argv[1], re.I), Path(argv[2])
        repo = Path(__file__).resolve().parents[3]
        if out.resolve().is_relative_to(repo) and "My Mods" not in out.resolve().parts:
            sys.exit("refusing: extract into My Mods/ (git-ignored) or outside the repo, never into tracked folders")
        n = 0
        for e in all_entries():
            if pat.search(e.name):
                dst = out / e.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(read_entry(e))
                n += 1
        print(n, "files extracted to", out)


def vars_of(e):
    return {k: getattr(e, k) for k in Entry.__slots__ if k != "pak"} | {"pak": e.pak.name}


if __name__ == "__main__":
    main(sys.argv[1:])
