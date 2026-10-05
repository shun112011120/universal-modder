# MODLOG: SoDcraft (State of Decay 2 ideas in Minecraft)

Journal for the mod. It becomes the field note at the end (`um kb new`).

## Setup
- **Route:** pattern 1 of `skills/mashup-mods` ("port the content"): State of Decay 2 merged into Minecraft. The
  mechanics are reimplemented in Fabric; the look and sound come from the owner's own SoD2 install through a local
  converter (see 2026-10-05). The repo ships code only; placeholder art is drawn by
  `tools/make_placeholder_textures.py`.
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
  - **Using SoD2's real content is the point of the project** (owner, 2026-10-05: "it was supposed to seem like a
    merge from game to game"). The early "never copy SoD2 files" line came from a session summary, not the owner's
    intent. SoD2's models, textures, sounds, guns and characters are extracted from the owner's own install and used
    in their Minecraft. Only the storage is limited: extracted files live in `My Mods/` (git-ignored, on the PC),
    never in this public repo, a release or a PR; the repo holds the mod code and the converter. `um publish check`
    before every push.

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

## v0.4.0: SoD2's own guns, rendered from the owner's install
- Converter: `tools/sod2pak.py` (SoD2 paks: custom v3 0x10003, plain index, raw LZ4 = method 0x103),
  `tools/sod2tex.py` (headerless BC1/BC3 `.hirez.ubulk` top mips), UE Viewer `-game=sod2` for skeletal meshes
  (object version 506, licensee 7; plain ue4.x tags fail), `tools/sod2_import.py` (14 guns -> local resource pack
  "SoD2 Assets" in the game dir, turned on in options.txt; `--preview` renders a contact sheet).
- 14 guns: M1911, Glock 17, M9, .44 revolver, 870, AA-12, AR-15, AK-47, SCAR-H, M14, Model 70, .50 bolt, MP5,
  Thompson. Calibres: .45, 9mm, .44, 12ga, 5.56, 7.62, .308, .30-06, .50. Shotguns fire 8 pellets; AA-12, AR-15,
  AK-47, SCAR-H, MP5 and Thompson are full-auto (hold right-click).
- Renderer: special item model `sodcraft:sod2_mesh` (registered through an accessor mixin on
  SpecialModelRenderers.ID_MAPPER); triangles submitted as degenerate quads with `submitCustomGeometry` and
  `RenderTypes.entityCutout(<SoD2 texture>)`. Without the pack, items fall back to the placeholder sprites.
- Known gaps: magazines and attachments live in SoD2's Mods_Depot and aren't attached yet (AR-15, AK-47, AA-12,
  M14, MP5 show without a magazine); hand/GUI transforms are first guesses, to tune in game; Minecraft lighting,
  not SoD2's PBR (normal/specular maps are unused).

## v0.3.0: SoD2's zombie types and blood plague
- `SodZombie` base: no daylight burning, no drowned conversion, never babies, no vanilla reinforcements; plague
  variants give blood plague on hit.
- Types: plague zombie (26 HP), feral + plague feral (fast 0.38, lunge via LeapAtTargetGoal, pins: slowness V 1.5 s),
  bloater (scale 1.25, bursts within 2.2 blocks or on death: poison II + nausea cloud r=4 for 10 s), juggernaut +
  plague juggernaut (scale 1.7, 150 HP, armor 10, no knockback, throws the player), armored zombie (iron helmet and
  chestplate, no drop; headshots get no bonus). Screamer now extends SodZombie.
- Blood plague (mob effect): +20% per plague hit, 60% hunger, 80% slowness + weakness, 100% 1.5 damage every 2 s.
  Plague samples drop from plague types; plague cure = 3 samples + glass bottle + sugar.
- Natural spawns: the first time a vanilla zombie loads it may become a freak (per 1000: plague 90, screamer 30,
  bloater 30, feral 25, armored 25, juggernaut 8, plague feral 6, plague juggernaut 3).
- Plague Heart waves: plague zombies + plain ones; ferals and bloaters from wave 2, plague ferals from wave 3, a
  screamer every other wave, a plague juggernaut every third wave; defenders are plague zombies / plague ferals.
- Look: placeholder skins on the zombie model for now. Next: SoD2's real meshes and textures through a custom
  renderer (the 1911 is extracted and previewed; see tools/sod2pak.py, sod2tex.py).

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
