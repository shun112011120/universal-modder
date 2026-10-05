# MODLOG: SoDcraft (State of Decay 2 ideas in Minecraft)

Journal for the mod. It becomes the field note at the end (`um kb new`).

## Setup
- **Route:** pattern 1 of `skills/mashup-mods` ("port the content"). State of Decay 2's ideas are rebuilt from
  scratch as Minecraft content. No State of Decay files, models, textures or sounds; only vanilla Minecraft
  sounds and particles, and textures drawn by `tools/make_placeholder_textures.py` (ComfyUI art later).
- **Versions** (checked on meta.fabricmc.net / maven.fabricmc.net on 2026-10-05; the same set builds
  `examples/minecraft-gta5-passthrough`): Minecraft Java **26.3** (newest stable; ships unobfuscated, so no
  mappings), Fabric Loader 0.19.5, Fabric API 0.161.0+26.3, Loom 1.18.2, Gradle 9.7.1, JDK 25.
- **Build:** GitHub Actions workflow "sodcraft mod" (`.github/workflows/sodcraft-mod.yml`) builds the jar and
  uploads it as the artifact `sodcraft-mod`. No JDK or Gradle needed on the owner's PC. Locally (optional, JDK 25):
  `./gradlew build` → `build/libs/sodcraft-0.1.0.jar`.
- **Mod id** `sodcraft`, package `com.sodcraft`.

## 2026-10-03
- Scan: Minecraft Launcher (Xbox app) installed, Bedrock installed. Java Edition never launched on this PC
  (`%APPDATA%\.minecraft` has only the launcher's version lists: no game files, no Fabric, no worlds). Nothing to
  back up yet.

## 2026-10-05: v0.1.0, first slice (not tested in game yet)
- API names checked against the real 26.3 client jar and Fabric API 0.161.0 (class-file listing, nothing
  decompiled or kept in the repo): `Identifier` (not ResourceLocation), `EntityTypes.ZOMBIE`,
  `monster.zombie.Zombie`, `ValueInput/ValueOutput` for block entity data, `Level.isDarkOutside()`,
  `BlockEntity.preRemoveSideEffects`, `Properties.setId(...)` required for blocks and items, no block codecs.
- **Plague Heart** (`sodcraft:plague_heart`): block + block entity, light 6, strength 5 (axe is fastest; TNT
  breaks it).
  - Once a second, if it's dark and a player is within 48 blocks: a wave every 30 s, the first one at once.
    Size 3 + waves sent so far (max 8), never more than 16 of its zombies alive. Every other wave adds a
    Screamer. Zombies spawn 6-14 blocks away on free ground near the heart's height and target the player.
  - Hitting it spawns 2-5 defenders right next to it (15 s cooldown), day or night.
  - Destroyed (mined, blown up, replaced): smoke, a break sound, "Plague Heart destroyed!", waves stop.
  - Saves its wave count and cooldown with the world.
- **Screamer** (`sodcraft:screamer`): a Zombie subclass, 14 HP, 1 attack. When its target player is within 24
  blocks and in sight: a loud scream (ghast scream, low pitch, sonic-boom puff), every zombie within 40 blocks
  targets the player with a speed boost; within 10 blocks the player gets slowness III + nausea. 10 s
  cooldown. Doesn't turn into a drowned.
- Placeholder textures: 16x16 heart block, 64x64 Screamer skin on the zombie layout.

## How to test (survival test world, difficulty Normal, cheats on)
1. `/give @s sodcraft:plague_heart`, place it on open flat ground, step ~10 blocks back.
2. `/time set night`. Within 1-2 s: "The Plague Heart calls the horde (wave 1)" and 3 zombies rise in smoke
   6-14 blocks from the heart. Wave 2 (30 s later) has 4 zombies + a Screamer.
3. Screamer alone: `/summon sodcraft:screamer ~ ~ ~8`, plus a few `/summon zombie ~20 ~ ~20`. When it sees you:
   scream, "A Screamer called N zombies!", the zombies come running; within 10 blocks you get slowness + nausea.
4. Hit the heart: "The Plague Heart lashes out!" and defenders spawn next to it.
5. Break it (axe is fastest): smoke, "Plague Heart destroyed!", no more waves.
6. Check `logs\latest.log` for `sodcraft` lines and for errors.
Zombies ignore creative mode, so test in survival (`/gamemode survival`).

## Ideas queue
Bloater (gas cloud on death), Juggernaut (tanky, throws), Feral (fast lunge), blood plague (builds up from hits,
cured by an item), Plague Hearts that get tougher per kill, natural Screamer spawns, ComfyUI textures, survivors,
morale, outposts, resources.
