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

## 2026-10-05: first in-game test of v0.1.0, and a new direction
- Setup (agent): launcher profile "SoDcraft" (Fabric Loader 0.19.5 for 26.3, profile json from meta.fabricmc.net +
  empty jar, the way fabric-installer does it; `launcher_profiles.json` backed up as
  `launcher_profiles.json.before-sodcraft`). Its own game dir: `<repo>/My Mods/minecraft-sodcraft` (git-ignored), with
  Fabric API 0.161.0+26.3 and the CI-built `sodcraft-0.1.0.jar` in `mods/`. No crash; "sodcraft loaded" in the log.
- No Plague Heart lines in the log: unclear whether the heart was placed (the player was killed by a husk).
  `/gamemode survival` came back "unknown or incomplete" on 26.3; use `/gamemode survival @s`.
- Owner's verdict: "doesn't feel like SoD at all". They want SoD2's character, movement and guns.
- Decisions:
  - Build SoD2's gameplay into Minecraft now (guns, then over-the-shoulder camera, stamina, dodge, survivor model).
  - Try the GTA-style passthrough (Minecraft blocks inside SoD2) later, starting with a feasibility test: does
    ReShade / UE4SS load into the Xbox app copy (its exe is unreadable from outside)?
  - **The owner allows SoD2's own models, textures and sounds, converted locally from their install, for personal
    use only.** Rule: anything taken from SoD2 goes to `My Mods/` (git-ignored), never into this repo, a release or
    a PR; `um publish check` before every push.

## v0.2.0: guns
- `GunItem`: hitscan (block clip + entity ray), magazine = durability bar, crouch + right-click or empty trigger
  reloads from inventory ammo, recoil kicks the camera (client side), spread, spark tracer, muzzle smoke, headshots
  (hit above eye height - 0.3) x2.5. Every shot alerts zombies in earshot (SoD2's noise rule). Creative: no ammo use.
  - Pistol: 12 rounds, 5 dmg, fire every 5 ticks, heard at 32 blocks. Recipe: `III / T` (iron, tripwire hook).
  - Hunting rifle: 5 rounds, 12 dmg, every 20 ticks, heard at 56 blocks. Recipe: `III / PT` (+ planks).
  - Ammo: iron + gunpowder = 12 pistol rounds; iron + 2 gunpowder = 6 rifle rounds.
- Plague Heart logs when placed and every 30 s while a player is near (dark outside? next wave?).

### Test v0.2.0
`/give @s sodcraft:pistol`, `/give @s sodcraft:pistol_ammo 64`, `/give @s sodcraft:rifle`, `/give @s sodcraft:rifle_ammo 32`,
`/gamemode survival @s`. Right-click shoots, crouch + right-click reloads. Shoot near zombies: they all turn on you.
Then the Plague Heart test again (place it, `/time set night`).

## How to test (v0.1 features) (survival test world, difficulty Normal, cheats on)
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
Over-the-shoulder camera, stamina (sprint, melee), dodge, survivor player model; SoD2 asset converter (local only); Bloater (gas cloud on death), Juggernaut (tanky, throws), Feral (fast lunge), blood plague (builds up from hits,
cured by an item), Plague Hearts that get tougher per kill, natural Screamer spawns, ComfyUI textures, survivors,
morale, outposts, resources.
