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


def sprite(name, rows, palette, seed):
    """A 16x16 item sprite from 16 strings of palette keys ('.' = transparent)."""
    rng = random.Random(seed)
    px = [[jitter(rng, palette[c], 8) if c != "." else (0, 0, 0, 0) for c in row.ljust(16, ".")] for row in rows]
    write_png(ASSETS / f"item/{name}.png", px, 16, 16)


GUN_PALETTE = {"k": (34, 34, 38), "g": (78, 80, 86), "l": (130, 134, 140), "w": (110, 72, 40), "d": (70, 44, 24)}
AMMO_PALETTE = {"b": (196, 150, 60), "y": (232, 196, 96), "c": (120, 80, 40), "k": (48, 40, 30), "s": (150, 150, 150)}


def guns():
    sprite("pistol", [
        "................",
        "................",
        "................",
        "....llllllllll..",
        "...lggggggggggk.",
        "...gkkkkkkkkkkk.",
        "...ggggggggggk..",
        "...gkk.k........",
        "...ggk..k.......",
        "...gggkk........",
        "...ggk..........",
        "..gggk..........",
        "..gggk..........",
        "..kkkk..........",
        "................",
        "................"], GUN_PALETTE, 3)
    sprite("rifle", [
        "................",
        "................",
        "................",
        "......kk........",
        ".....kllk.......",
        "wwwwwgggggllllll",
        "wddwwgkkkkkkkkkk",
        "wddwggkgg.......",
        "wwww..kk........",
        "ww....k.........",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................"], GUN_PALETTE, 4)
    sprite("pistol_ammo", [
        "................",
        "................",
        "................",
        "....y..y..y.....",
        "...yby.yby.yb...",
        "...bbb.bbb.bb...",
        "...bbb.bbb.bb...",
        "...ccc.ccc.cc...",
        "..kkkkkkkkkkkk..",
        "..kssssssssssk..",
        "..kssssssssssk..",
        "..kkkkkkkkkkkk..",
        "................",
        "................",
        "................",
        "................"], AMMO_PALETTE, 5)
    sprite("rifle_ammo", [
        "................",
        ".....y....y.....",
        "....yby..yby....",
        "....bbb..bbb....",
        "....bbb..bbb....",
        "....bbb..bbb....",
        "....bbb..bbb....",
        "....bbb..bbb....",
        "....ccc..ccc....",
        "..kkkkkkkkkkkk..",
        "..kssssssssssk..",
        "..kssssssssssk..",
        "..kkkkkkkkkkkk..",
        "................",
        "................",
        "................"], AMMO_PALETTE, 6)


def zombie_skin(name, skin, shirt, pants, eyes, mouth=(30, 8, 8), blood=None, seed=1, bulk=False):
    """A 64x64 skin on the zombie layout: flat colours with noise, eyes and mouth on the head's front face."""
    rng = random.Random(seed)
    px = [[(0, 0, 0, 0)] * 64 for _ in range(64)]

    def fill(x0, y0, x1, y1, color, amount=12):
        for y in range(y0, y1):
            for x in range(x0, x1):
                px[y][x] = jitter(rng, color, amount)

    fill(0, 0, 32, 16, skin)
    fill(16, 16, 40, 32, shirt)
    fill(40, 16, 56, 32, skin)
    fill(32, 48, 48, 64, skin)
    fill(0, 16, 16, 32, pants)
    fill(16, 48, 32, 64, pants)
    if bulk:  # boils / swelling
        for _ in range(40):
            x, y = rng.choice([(rng.randrange(16, 40), rng.randrange(16, 32)), (rng.randrange(0, 32), rng.randrange(0, 16))])
            px[y][x] = jitter(rng, (196, 186, 92), 10)
    if blood:
        for _ in range(60):
            x, y = rng.randrange(16, 40), rng.randrange(16, 32)
            px[y][x] = jitter(rng, blood, 14)
        for _ in range(12):
            px[rng.randrange(8, 16)][rng.randrange(8, 16)] = jitter(rng, blood, 10)
    for x, y in ((9, 11), (10, 11), (13, 11), (14, 11)):
        px[y][x] = eyes + (255,)
    for y in range(13, 15):
        for x in range(10, 14):
            px[y][x] = mouth + (255,)
    write_png(ASSETS / f"entity/{name}.png", px, 64, 64)


RED_EYES = (230, 30, 30)
DEAD_EYES = (210, 205, 150)


def zombies():
    zombie_skin("plague_zombie", (104, 120, 92), (80, 40, 40), (52, 52, 70), RED_EYES, blood=(140, 14, 22), seed=21)
    zombie_skin("feral", (78, 74, 70), (40, 36, 34), (34, 34, 40), DEAD_EYES, mouth=(150, 20, 24), seed=22)
    zombie_skin("plague_feral", (82, 66, 64), (52, 24, 24), (34, 30, 34), RED_EYES, mouth=(170, 20, 24), blood=(150, 16, 24), seed=23)
    zombie_skin("bloater", (150, 160, 86), (110, 112, 70), (70, 74, 54), DEAD_EYES, mouth=(70, 80, 20), seed=24, bulk=True)
    zombie_skin("juggernaut", (120, 116, 110), (60, 58, 56), (44, 44, 48), DEAD_EYES, seed=25)
    zombie_skin("plague_juggernaut", (124, 92, 88), (70, 30, 30), (44, 36, 40), RED_EYES, blood=(150, 16, 24), seed=26)
    zombie_skin("armored_zombie", (100, 116, 96), (28, 34, 54), (24, 28, 44), DEAD_EYES, seed=27)


def plague_items():
    pal = {"g": (190, 200, 210), "w": (230, 236, 240), "r": (150, 16, 28), "R": (210, 40, 50), "c": (110, 80, 50),
           "G": (90, 190, 120), "l": (150, 230, 170)}
    sprite("plague_sample", [
        "................", "................", "......cc........", "......cc........", ".....gwwg.......", ".....grRg.......",
        ".....grRg.......", ".....grrg.......", ".....grrg.......", ".....grrg.......", ".....grrg.......", "......gg........",
        "................", "................", "................", "................"], pal, 31)
    sprite("plague_cure", [
        "................", "......cc........", "......cc........", "......gg........", ".....g..g.......", "....g....g......",
        "...gGGGGGGg.....", "...gGlGGGGg.....", "...gGGlGGGg.....", "...gGGGGGGg.....", "...gGGGGGGg.....", "....gGGGGg......",
        ".....gggg.......", "................", "................", "................"], pal, 32)
    rng = random.Random(33)  # mob effect icon, 18x18
    px = [[(0, 0, 0, 0)] * 18 for _ in range(18)]
    for y in range(18):
        for x in range(18):
            d = ((x - 8.5) ** 2 + (y - 9.5) ** 2) ** 0.5
            if d < 6.5 or (y < 9 and abs(x - 8.5) < 2.5 and y > 1):
                px[y][x] = jitter(rng, (150, 16, 28) if d > 3 else (220, 60, 60), 10)
    ASSETS.joinpath("mob_effect").mkdir(parents=True, exist_ok=True)
    write_png(ASSETS / "mob_effect/blood_plague.png", px, 18, 18)


if __name__ == "__main__":
    plague_heart()
    screamer()
    guns()
    zombies()
    plague_items()
