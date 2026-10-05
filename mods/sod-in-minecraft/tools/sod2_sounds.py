"""State of Decay 2's own sounds for SoDcraft, from the owner's install, into the local "SoD2 Assets" pack.

    python tools/sod2_sounds.py [--game-dir DIR]

SoD2's audio is Wwise: banks (*.bnk, sounds embedded in DIDX/DATA) and loose *.wem, all in WwiseAudio/Windows;
SoundbanksInfo.xml names every sound (File Id -> ShortName, e.g. wpn_pstl_45_colt1911_fire_impulse_02.wav).
For every SoDcraft sound event in EVENTS this finds the matching SoD2 sounds, decodes them with vgmstream
(data/tools/vgmstream), builds each variant with ffmpeg (data/win/ffmpeg: `um win setup`), and writes mono .ogg files
plus a sounds.json that replaces the mod's fallback (vanilla) sounds:
  - gunshots: SoD2 layers each shot (impulse + body + mechanism + outdoor tail); they're mixed back together,
  - reloads: the steps (mag out, mag in, slide...) in order,
  - voices: up to four variants each.
Everything lands under My Mods/ (git-ignored); never commit or share it.
"""
import json
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
WWISE = Path(r"C:\XboxGames\State of Decay 2\Content\StateOfDecay2\Content\WwiseAudio\Windows")
VGM = REPO / "data/tools/vgmstream/vgmstream-cli.exe"
FFMPEG = REPO / "data/win/ffmpeg/bin/ffmpeg.exe"
GAME_DIR = REPO / "My Mods/minecraft-sodcraft"
PACK = "SoD2 Assets"

# gun -> (SoD2 gunshot folder, SoD2 reload folder)
GUNS = {
    "pistol": ("wpn_pstl_45_colt1911", "wpn_pstl_45_v1"),
    "glock17": ("wpn_pstl_9mm_walther", "wpn_pstl_9mm"),
    "m9": ("wpn_pstl_9mm_beretta", "wpn_pstl_9mm"),
    "revolver44": ("wpn_rev_44_sw629", "wpn_rev_44"),
    "shotgun870": ("wpn_shtgn_870_win1300", "wpn_shtgn_870"),
    "aa12": ("wpn_shtgn_aa12", "wpn_shtgn_auto"),
    "ar15": ("wpn_ar_556_ar15", "wpn_ar_556"),
    "ak47": ("wpn_ar_762_ak47", "wpn_ar_762"),
    "scarh": ("wpn_ar_762_scar", "wpn_ar_762"),
    "m14": ("wpn_ar_762_fal", "wpn_rfl_762"),
    "rifle": ("wpn_rfl_762_rem700p", "wpn_rfl_50"),  # its own reload set is streamed elsewhere: the bolt-action one
    "bolt50": ("wpn_rfl_50_m82a1", "wpn_rfl_50"),
    "mp5": ("wpn_smg_9mm_uzi", "wpn_smg_9mm"),
    "thompson": ("wpn_smg_45_kimber", "wpn_smg_45"),
}
SHOT_LAYERS = [("fire_impulse", 1.0), ("fire_body", 1.0), ("fire_mech", 0.6), ("fire_tail_ext_short", 0.8)]
# reload steps in order: the first keyword that matches a SoD2 category decides its place
RELOAD_ORDER = ["out", "eject", "open", "fumble", "in", "insert", "load", "shell", "back", "pump", "bolt", "charge", "release", "close", "forward"]

# event -> regex on the SoD2 file name (voices: up to 4 variants)
VOICES = {
    "screamer.scream": r"\\zdx_screamer_(var_)?yell_\d+\.wav$",
    "screamer.ambient": r"\\zdx_screamer_idle_\d+\.wav$",
    "screamer.hurt": r"\\zdx_screamer_pain_(sml|lrg)_\d+\.wav$",
    "screamer.death": r"\\zdx_screamer_death_\d+\.wav$",
    "bloater.ambient": r"\\zdx_bloater_idle_\d+\.wav$",
    "bloater.burst": r"\\zdx_bloater_death_\d+\.wav$",
    "bloater.hurt": r"\\zdx_bloater_pain_\d+\.wav$",
    "feral.ambient": r"\\zdx_frl_idle(_notice)?_\d+\.wav$",
    "feral.attack": r"\\zdx_frl_(claw|lunge)_\d+\.wav$",
    "feral.hurt": r"\\zdx_frl_pain_\d+\.wav$",
    "feral.death": r"\\zdx_frl_death_\d+\.wav$",
    "juggernaut.attack": r"\\mle_frk_jugg_punch_\d+\.wav$",
    # plain zombies keep vanilla voices: SoD2 streams its generic zombie voices from somewhere these banks do not hold
    "gun.dryfire": r"\\wpn_pstl_45_colt1911_dryfire_\d+\.wav$",
}


def names_by_id():
    x = (WWISE / "SoundbanksInfo.xml").read_text(encoding="utf-8")
    return {int(i): n for i, n in re.findall(r'<File Id="(\d+)"[^>]*>\s*<ShortName>([^<]+)</ShortName>', x)}


def media_index():
    """Wwise media id -> (file, offset, size): embedded in banks (DIDX + DATA) or loose <id>.wem."""
    idx = {}
    for wem in WWISE.rglob("*.wem"):
        if wem.stem.isdigit():
            idx[int(wem.stem)] = (wem, 0, wem.stat().st_size)
    for bnk in WWISE.rglob("*.bnk"):
        b = bnk.read_bytes()
        i, didx, data = 0, None, None
        while i + 8 <= len(b):
            tag, size = b[i:i + 4], struct.unpack_from("<I", b, i + 4)[0]
            if tag == b"DIDX":
                didx = (i + 8, size)
            elif tag == b"DATA":
                data = i + 8
            i += 8 + size
        if didx and data is not None:
            for k in range(didx[1] // 12):
                mid, off, size = struct.unpack_from("<III", b, didx[0] + 12 * k)
                idx.setdefault(mid, (bnk, data + off, size))
    return idx


class Decoder:
    def __init__(self, media):
        self.media = media
        self.tmp = Path(tempfile.mkdtemp(prefix="sod2snd"))

    def wav(self, mid):
        out = self.tmp / f"{mid}.wav"
        if not out.exists():
            f, off, size = self.media[mid]
            with open(f, "rb") as fh:
                fh.seek(off)
                (self.tmp / f"{mid}.wem").write_bytes(fh.read(size))
            subprocess.run([str(VGM), "-o", str(out), str(self.tmp / f"{mid}.wem")], capture_output=True, check=True)
        return out


def ffmpeg(inputs, filt, out):
    cmd = [str(FFMPEG), "-y", "-loglevel", "error"]
    for i in inputs:
        cmd += ["-i", str(i)]
    cmd += ["-filter_complex", filt, "-ac", "1", "-c:a", "libvorbis", "-q:a", "5", str(out)]
    subprocess.run(cmd, check=True)


def main(argv):
    global GAME_DIR
    if "--game-dir" in argv:
        GAME_DIR = Path(argv[argv.index("--game-dir") + 1])
    names = names_by_id()
    media = media_index()
    dec = Decoder(media)
    by_name = {}
    for mid, n in names.items():
        if mid in media:
            by_name.setdefault(n, mid)
    print(f"{len(names)} named sounds, {len(media)} media, {len(by_name)} usable")

    pack = GAME_DIR / "resourcepacks" / PACK / "assets/sodcraft"
    out_dir = pack / "sounds/sod2"
    out_dir.mkdir(parents=True, exist_ok=True)
    sounds = {}

    def files(pattern):
        return sorted(n for n in by_name if re.search(pattern, n, re.I))

    for gun, (shot, reload) in GUNS.items():
        # gunshot variants: layer k of each kind (falling back to the first of that kind)
        layers = {kind: files(rf"\\{shot}\\{shot}_{kind}_\d+\.wav$") for kind, _ in SHOT_LAYERS}
        n_var = min(3, max((len(v) for v in layers.values()), default=0))
        variants = []
        for k in range(n_var):
            ins, weights = [], []
            for kind, w in SHOT_LAYERS:
                if layers[kind]:
                    ins.append(dec.wav(by_name[layers[kind][min(k, len(layers[kind]) - 1)]]))
                    weights.append(str(w))
            name = f"gun_{gun}_fire_{k + 1}"
            filt = "".join(f"[{i}:a]" for i in range(len(ins))) + f"amix=inputs={len(ins)}:normalize=0:weights={' '.join(weights)},alimiter=limit=0.95"
            ffmpeg(ins, filt, out_dir / f"{name}.ogg")
            variants.append({"name": f"sodcraft:sod2/{name}", "attenuation_distance": 64})
        if variants:
            sounds[f"gun.{gun}.fire"] = {"replace": True, "sounds": variants}

        # reload: one take of every step, in order
        steps = {}
        for n in files(rf"\\{reload}\\[^\\]+\.wav$"):
            cat = re.sub(r"_\d+\.wav$", "", n.split("\\")[-1])
            steps.setdefault(cat, n)

        def order(cat):
            tail = cat.split("rld_")[-1]
            return next((i for i, key in enumerate(RELOAD_ORDER) if key in tail), len(RELOAD_ORDER))

        seq = [steps[c] for c in sorted(steps, key=order)][:5]
        if seq:
            ins = [dec.wav(by_name[n]) for n in seq]
            name = f"gun_{gun}_reload"
            filt = "".join(f"[{i}:a]aresample=48000,aformat=channel_layouts=mono[a{i}];" for i in range(len(ins)))
            filt += "".join(f"[a{i}]" for i in range(len(ins))) + f"concat=n={len(ins)}:v=0:a=1"
            ffmpeg(ins, filt, out_dir / f"{name}.ogg")
            sounds[f"gun.{gun}.reload"] = {"replace": True, "sounds": [f"sodcraft:sod2/{name}"]}
        print(f"{gun:11s} shots {len(variants)}  reload steps {len(seq)}")

    for event, pattern in VOICES.items():
        chosen = files(pattern)[:4]
        variants = []
        for k, n in enumerate(chosen):
            name = event.replace(".", "_") + f"_{k + 1}"
            ffmpeg([dec.wav(by_name[n])], "[0:a]anull", out_dir / f"{name}.ogg")
            variants.append(f"sodcraft:sod2/{name}")
        if variants:
            sounds[event] = {"replace": True, "sounds": variants}
        print(f"{event:18s} {len(variants)} variants")

    (pack / "sounds.json").write_text(json.dumps(sounds, indent=1))
    print(f"{len(sounds)} events -> {pack / 'sounds.json'}")


if __name__ == "__main__":
    main(sys.argv[1:])
