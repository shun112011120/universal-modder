"""Draw the mod's placeholder textures from code (no game files, no dependencies):

    python tools/make_placeholder_textures.py

- textures/block/plague_heart.png  16x16: a dark, veined lump of flesh with a glowing core.
- textures/entity/screamer.png     64x64: a skin for the zombie model, gaunt and grey with a gaping mouth.

Replace them with ComfyUI art later (Universal Modder app -> Art -> "Make sprite..." at 16x16); the entity skin
has to follow the 64x64 humanoid UV layout, so keep this script's layout if you repaint it.
"""
import random
import struct
import zlib
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "src/main/resources/assets/sodcraft/textures"


def write_png(path, pixels, w, h):
    """pixels: list of rows of (r, g, b, a)."""
    raw = b"".join(b"\x00" + bytes(c for px in row for c in px) for row in pixels)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    print("wrote", path.relative_to(ASSETS).as_posix(), f"({w}x{h})")


def jitter(rng, c, amount):
    return tuple(max(0, min(255, v + rng.randint(-amount, amount))) for v in c[:3]) + (255,)


def plague_heart():
    rng = random.Random(7)
    flesh, dark, vein, core, rim = (110, 18, 28), (52, 8, 20), (190, 40, 46), (255, 120, 90), (34, 6, 22)
    px = [[jitter(rng, flesh, 14) for _ in range(16)] for _ in range(16)]
    for y in range(16):
        for x in range(16):
            d = ((x - 7.5) ** 2 + (y - 7.5) ** 2) ** 0.5
            if d > 6.5:
                px[y][x] = jitter(rng, dark, 8)
            if x in (0, 15) or y in (0, 15):
                px[y][x] = jitter(rng, rim, 6)
    # veins: random walks out from the middle
    for _ in range(5):
        x, y = 7 + rng.randint(0, 1), 7 + rng.randint(0, 1)
        for _ in range(9):
            if 0 < x < 15 and 0 < y < 15:
                px[y][x] = jitter(rng, vein, 10)
            x += rng.choice((-1, 0, 1))
            y += rng.choice((-1, 0, 1))
    for y in range(6, 10):
        for x in range(6, 10):
            if (x, y) not in ((6, 6), (9, 6), (6, 9), (9, 9)):
                px[y][x] = jitter(rng, core, 12)
    write_png(ASSETS / "block/plague_heart.png", px, 16, 16)


def screamer():
    rng = random.Random(11)
    w = h = 64
    px = [[(0, 0, 0, 0)] * w for _ in range(h)]
    skin, shirt, pants, shadow = (128, 140, 118), (70, 62, 58), (44, 48, 60), (88, 98, 84)

    def fill(x0, y0, x1, y1, color, amount=10):
        for y in range(y0, y1):
            for x in range(x0, x1):
                px[y][x] = jitter(rng, color, amount)

    # humanoid 64x64 layout
    fill(0, 0, 32, 16, skin)  # head (all faces)
    fill(16, 16, 40, 32, shirt)  # body
    fill(40, 16, 56, 32, skin)  # right arm
    fill(40, 20, 56, 23, shirt, 6)  # torn sleeve
    fill(32, 48, 48, 64, skin)  # left arm
    fill(32, 52, 48, 55, shirt, 6)
    fill(0, 16, 16, 32, pants)  # right leg
    fill(16, 48, 32, 64, pants)  # left leg
    # ribs showing through the torn shirt front (body front: x 20..28, y 20..32)
    for y in (23, 25, 27):
        for x in range(21, 27):
            px[y][x] = jitter(rng, shadow, 6)
    # face (head front: x 8..16, y 8..16): sunken eyes, gaping mouth
    for x, y in ((9, 10), (10, 10), (13, 10), (14, 10)):
        px[y][x] = (24, 20, 20, 255)
    px[11][9], px[11][14] = (230, 220, 120, 255), (230, 220, 120, 255)
    for y in range(12, 16):
        for x in range(10, 14):
            px[y][x] = (20, 4, 6, 255)
    for x in range(10, 14):
        px[15][x] = (120, 20, 26, 255)
    write_png(ASSETS / "entity/screamer.png", px, w, h)


if __name__ == "__main__":
    plague_heart()
    screamer()
