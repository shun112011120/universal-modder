"""Bring State of Decay 2's own guns into SoDcraft, from the owner's SoD2 install, on the owner's PC.

    python tools/sod2_import.py [--game-dir DIR] [--preview]

For each gun in GUNS it extracts the SoD2 files (tools/sod2pak.py), exports the mesh with UE Viewer's sod2 mode
(data/tools/umodel), decodes the full-resolution colour texture (tools/sod2tex.py), and writes a resource pack
"SoD2 Assets" into the game dir's resourcepacks/ with, per gun:
    assets/sodcraft/sod2/<id>.mesh                  the mesh (format below), in item space
    assets/sodcraft/textures/sod2/<id>.png          SoD2's colour texture
    assets/sodcraft/items/<id>.json                 the item drawn by the mod's sodcraft:sod2_mesh renderer
    assets/sodcraft/models/item/<id>_sod2.json      hand/GUI transforms
It also turns the pack on in the game dir's options.txt (close Minecraft first). Nothing here is committed: the pack
and the intermediate files live under My Mods/ (git-ignored).

.mesh: "SODM", int32 version=1, int32 vertices, int32 indices, then per vertex 8 float32 (x y z nx ny nz u v),
then int32 indices (triangles); little-endian. Item space: muzzle towards +x, top +y, centred on (0.5, 0.5, 0.5).
--preview also renders a contact sheet of every gun to My Mods/sod2-export/guns.png.
"""
import json
import math
import struct
import subprocess
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import sod2pak  # noqa: E402
import sod2tex  # noqa: E402

UMODEL = REPO / "data/tools/umodel/umodel_64.exe"
WORK = REPO / "My Mods"
EXTRACT = WORK / "sod2-extract"
EXPORT = WORK / "sod2-export"
GAME_DIR = WORK / "minecraft-sodcraft"
PACK_NAME = "SoD2 Assets"
UNITS_PER_METRE = 3.4  # a 25 cm pistol is ~0.85 of a block in item space; hand/GUI transforms scale per gun

# mod item id -> (SoD2 folder under Art/Weapons, mesh package)
GUNS = {
    "pistol": ("Pistol_1911/Pistol_1911_01", "pistol_45_1911_01"),
    "glock17": ("Pistol_G_17", "pistol_g_17"),
    "m9": ("Pistol_M9", None),
    "revolver44": ("Revo_Model_29", "revo_model_29"),
    "shotgun870": ("Shotgun_870_01", "shotgun_870_01"),
    "aa12": ("Shotgun_AA12", None),
    "ar15": ("Assault_AR15_01", "assault_ar15"),
    "ak47": ("Assault_AK_47", "assault_ak47"),
    "scarh": ("Assault_Scar_H", None),
    "m14": ("Rifle_M14", None),
    "rifle": ("Rifle_Model_70", "rifle_model_70"),
    "bolt50": ("Pack11_Rifle_Bolt50", "pack11_rifle_bolt50"),
    "mp5": ("Smg_MP5", "smg_mp5"),
    "thompson": ("SMG_Thompson_01", None),
}


def extract(folder):
    prefix = f"StateOfDecay2/Content/Art/Weapons/{folder}/"
    entries = [e for e in sod2pak.all_entries() if e.name.startswith(prefix)]
    for e in entries:
        dst = EXTRACT / e.name
        if not dst.exists() or dst.stat().st_size != e.usize:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(sod2pak.read_entry(e))
    return [EXTRACT / e.name for e in entries]


def pick_mesh(files):
    """The mesh package: the biggest .uasset that isn't a texture or material."""
    cands = [f for f in files if f.suffix == ".uasset" and not any(f.stem.lower().endswith(s) for s in ("_a", "_n", "_s", "_inst", "_m", "_mat"))
             and "_mat_" not in f.stem.lower()]
    return max(cands, key=lambda f: f.stat().st_size).stem if cands else None


def umodel_export(name, *flags):
    out = subprocess.run([str(UMODEL), f"-path={EXTRACT}", "-game=sod2", "-export", *flags, f"-out={EXPORT}", name],
                         capture_output=True, text=True, cwd=str(EXPORT))
    if "Exported" not in out.stdout:
        raise RuntimeError(f"umodel {name}: {out.stdout[-400:]}")


def albedo(files, gun_id):
    """Full-res colour map: the .hirez.ubulk top mip if there is one, else UE Viewer's PNG."""
    out = EXPORT / "textures" / f"{gun_id}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    hirez = sorted((f for f in files if f.name.lower().endswith("_a.hirez.ubulk")), key=lambda f: -f.stat().st_size)
    if hirez:
        data = hirez[0].read_bytes()
        for fmt in ("bc1", "bc3"):
            side = int(round((len(data) * (2 if fmt == "bc1" else 1)) ** 0.5))
            if side * side == len(data) * (2 if fmt == "bc1" else 1) and side & (side - 1) == 0:
                sod2tex.write_png(out, sod2tex.decode(data, side, side, fmt), side, side)
                return out
    tex = [f for f in files if f.suffix == ".uasset" and f.stem.lower().endswith("_a")]
    if not tex:
        raise RuntimeError(f"{gun_id}: no colour texture")
    umodel_export(tex[0].stem, "-png")
    png = next(EXPORT.rglob(tex[0].stem + ".png"))
    out.write_bytes(png.read_bytes())
    return out


def load_gltf(path):
    g = json.loads(path.read_text())
    buf = (path.parent / g["buffers"][0]["uri"]).read_bytes()

    def acc(i):
        a = g["accessors"][i]
        v = g["bufferViews"][a["bufferView"]]
        off = v.get("byteOffset", 0) + a.get("byteOffset", 0)
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
        fmt = {5126: "f", 5123: "H", 5125: "I", 5121: "B"}[a["componentType"]]
        stride = v.get("byteStride", struct.calcsize(fmt) * n)
        return [struct.unpack_from("<" + fmt * n, buf, off + k * stride) for k in range(a["count"])]

    verts, idx = [], []
    for mesh in g["meshes"]:
        for p in mesh["primitives"]:
            base = len(verts)
            P, N, T = acc(p["attributes"]["POSITION"]), acc(p["attributes"]["NORMAL"]), acc(p["attributes"]["TEXCOORD_0"])
            verts += [(*P[k], *N[k], *T[k]) for k in range(len(P))]
            idx += [base + i[0] for i in acc(p["indices"])]
    return verts, idx


def to_item_space(verts):
    """SoD2 (glTF export): length along z with the muzzle at -z, up +y. Item space: muzzle +x, centred on 0.5."""
    out = [(-z, y, x, -nz, ny, nx, u, v) for (x, y, z, nx, ny, nz, u, v) in verts]
    lo = [min(p[i] for p in out) for i in range(3)]
    hi = [max(p[i] for p in out) for i in range(3)]
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]
    s = UNITS_PER_METRE
    out = [((x - c[0]) * s + 0.5, (y - c[1]) * s + 0.5, (z - c[2]) * s + 0.5, nx, ny, nz, u, v) for (x, y, z, nx, ny, nz, u, v) in out]
    return out, (hi[0] - lo[0]) * s


def write_mesh(path, verts, idx):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"SODM" + struct.pack("<iii", 1, len(verts), len(idx)))
        for v in verts:
            f.write(struct.pack("<8f", *v))
        f.write(struct.pack(f"<{len(idx)}i", *idx))


def display(length):
    """Hand/GUI transforms for a gun `length` item-space units long (muzzle +x)."""
    gui = round(min(1.0, 0.95 / length), 3)
    held = round(min(0.85, 0.85 / max(length, 0.85)) * 1.0, 3)
    return {
        "thirdperson_righthand": {"rotation": [0, -90, 0], "translation": [0, 2.5, 1.5], "scale": [held, held, held]},
        "thirdperson_lefthand": {"rotation": [0, 90, 0], "translation": [0, 2.5, 1.5], "scale": [held, held, held]},
        "firstperson_righthand": {"rotation": [0, -95, 5], "translation": [1.5, 3.0, -1.0], "scale": [held, held, held]},
        "firstperson_lefthand": {"rotation": [0, 85, -5], "translation": [1.5, 3.0, -1.0], "scale": [held, held, held]},
        "gui": {"rotation": [0, 0, 35], "translation": [0, 0, 0], "scale": [gui, gui, gui]},
        "ground": {"rotation": [0, 0, 0], "translation": [0, 2, 0], "scale": [0.5, 0.5, 0.5]},
        "fixed": {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [gui, gui, gui]},
    }


def write_pack(guns):
    pack = GAME_DIR / "resourcepacks" / PACK_NAME
    a = pack / "assets/sodcraft"
    (pack).mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(json.dumps({"pack": {
        "description": "State of Decay 2's own guns, converted from your install (personal use, don't share)",
        "min_format": 97, "max_format": 97}}, indent=2))
    for gun_id, (verts, idx, tex, length) in guns.items():
        write_mesh(a / "sod2" / f"{gun_id}.mesh", verts, idx)
        (a / "textures/sod2").mkdir(parents=True, exist_ok=True)
        (a / "textures/sod2" / f"{gun_id}.png").write_bytes(tex.read_bytes())
        (a / "models/item").mkdir(parents=True, exist_ok=True)
        (a / "models/item" / f"{gun_id}_sod2.json").write_text(json.dumps({
            "textures": {"particle": f"sodcraft:sod2/{gun_id}"}, "display": display(length)}, indent=1))
        (a / "items").mkdir(parents=True, exist_ok=True)
        (a / "items" / f"{gun_id}.json").write_text(json.dumps({"model": {
            "type": "minecraft:special", "base": f"sodcraft:item/{gun_id}_sod2",
            "model": {"type": "sodcraft:sod2_mesh", "mesh": gun_id}}}, indent=1))
    return pack


def enable_pack():
    opts = GAME_DIR / "options.txt"
    entry = f'"file/{PACK_NAME}"'
    if not opts.exists():
        opts.write_text(f'resourcePacks:["vanilla","fabric",{entry}]\n')
        return "options.txt created"
    lines = opts.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("resourcePacks:"):
            if entry in line:
                return "already on"
            packs = json.loads(line.split(":", 1)[1])
            packs.append(f"file/{PACK_NAME}")
            lines[i] = "resourcePacks:" + json.dumps(packs, separators=(",", ":"))
            break
    else:
        lines.append(f'resourcePacks:["vanilla","fabric",{entry}]')
    opts.write_text("\n".join(lines) + "\n")
    return "turned on"


def contact_sheet(guns, out):
    """Flat-shaded, textured side views of every gun (pure Python), to check orientation and texturing."""
    cell_w, cell_h, cols = 360, 200, 4
    rows = (len(guns) + cols - 1) // cols
    W, H = cell_w * cols, cell_h * rows
    img = bytearray([236, 234, 228] * W * H)
    for n, (gun_id, (verts, idx, tex, _)) in enumerate(guns.items()):
        tw, th, traw = _read_png(tex)
        ox, oy = (n % cols) * cell_w, (n // cols) * cell_h
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        sc = min((cell_w - 30) / (max(xs) - min(xs)), (cell_h - 30) / (max(ys) - min(ys)))
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        S = [(ox + cell_w / 2 + (v[0] - cx) * sc, oy + cell_h / 2 - (v[1] - cy) * sc, -v[2]) for v in verts]
        zb = {}
        for t in range(0, len(idx), 3):
            a, b, c = idx[t], idx[t + 1], idx[t + 2]
            (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = S[a], S[b], S[c]
            den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(den) < 1e-9:
                continue
            for py in range(max(oy, int(min(y0, y1, y2))), min(oy + cell_h, int(max(y0, y1, y2)) + 1)):
                for px in range(max(ox, int(min(x0, x1, x2))), min(ox + cell_w, int(max(x0, x1, x2)) + 1)):
                    w0 = ((y1 - y2) * (px - x2) + (x2 - x1) * (py - y2)) / den
                    w1 = ((y2 - y0) * (px - x2) + (x0 - x2) * (py - y2)) / den
                    w2 = 1 - w0 - w1
                    if w0 < 0 or w1 < 0 or w2 < 0:
                        continue
                    z = w0 * z0 + w1 * z1 + w2 * z2
                    k = py * W + px
                    if zb.get(k, 1e9) <= z:
                        continue
                    zb[k] = z
                    u = w0 * verts[a][6] + w1 * verts[b][6] + w2 * verts[c][6]
                    v = w0 * verts[a][7] + w1 * verts[b][7] + w2 * verts[c][7]
                    nz = w0 * verts[a][5] + w1 * verts[b][5] + w2 * verts[c][5]
                    shade = 0.55 + 0.6 * abs(nz)
                    x_ = min(tw - 1, max(0, int((u % 1) * tw)))
                    y_ = min(th - 1, max(0, int((v % 1) * th)))
                    o = y_ * (tw * 4 + 1) + 1 + x_ * 4
                    img[k * 3:k * 3 + 3] = bytes(min(255, int(ch * shade * 1.2)) for ch in traw[o:o + 3])
    raw = b"".join(b"\x00" + bytes(img[y * W * 3:(y + 1) * W * 3]) for y in range(H))

    def chunk(k, d):
        return struct.pack(">I", len(d)) + k + d + struct.pack(">I", zlib.crc32(k + d) & 0xFFFFFFFF)

    out.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _read_png(path):
    b = path.read_bytes()
    w, h = struct.unpack(">II", b[16:24])
    color = b[25]
    i, d = 8, b""
    while i < len(b):
        n = struct.unpack(">I", b[i:i + 4])[0]
        if b[i + 4:i + 8] == b"IDAT":
            d += b[i + 8:i + 8 + n]
        i += 12 + n
    raw = zlib.decompress(d)
    bpp = {6: 4, 2: 3, 4: 2, 0: 1}[color]
    stride = w * bpp
    rows, prev = [], bytearray(stride)
    for y in range(h):  # undo PNG row filters
        f = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = line
        rgba = bytearray()
        for x in range(w):
            px = line[x * bpp:(x + 1) * bpp]
            rgba += bytes((px[0], px[0], px[0], 255)) if bpp <= 2 else bytes((px[0], px[1], px[2], 255))
        rows.append(b"\x00" + bytes(rgba))
    return w, h, b"".join(rows)


def main(argv):
    global GAME_DIR
    if "--game-dir" in argv:
        GAME_DIR = Path(argv[argv.index("--game-dir") + 1])
    EXPORT.mkdir(parents=True, exist_ok=True)
    done = {}
    for gun_id, (folder, mesh) in GUNS.items():
        try:
            files = extract(folder)
            mesh = mesh or pick_mesh(files)
            umodel_export(mesh, "-gltf")
            gltf = next(EXPORT.rglob(mesh + ".gltf"))
            verts, idx = load_gltf(gltf)
            verts, length = to_item_space(verts)
            tex = albedo(files, gun_id)
            done[gun_id] = (verts, idx, tex, length)
            print(f"{gun_id:11s} {folder:36s} {len(verts):6d} verts {len(idx) // 3:6d} tris  length {length:.2f}")
        except Exception as e:  # keep going: one odd gun shouldn't stop the rest
            print(f"{gun_id:11s} FAILED: {e}")
    pack = write_pack(done)
    print(f"pack: {pack} ({len(done)} guns); options: {enable_pack()}")
    if "--preview" in argv:
        contact_sheet(done, EXPORT / "guns.png")
        print("preview:", EXPORT / "guns.png")


if __name__ == "__main__":
    main(sys.argv[1:])
