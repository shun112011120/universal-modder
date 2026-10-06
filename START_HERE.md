# Start here: where this project is

A new agent session reads this first, says in a few lines where things stand, then carries on with **Next
steps**. At the end of a session, update **Where we are** and **Next steps** (keep it short) and commit.

Personal details (PC specs, installed models, folders) are in `SETUP_SUMMARY.md` next to this file when the
owner has copied it in. It's git-ignored: read it, never commit it.

## The owner's preferences
- Ask before any download over ~100 MB or any install (loaders, Java, Gradle, Python packages). Give the name,
  where it comes from and its size first.
- Ask before deleting anything. Keep existing setups working; make new variants instead of overwriting.
- Short, practical answers.
- The GPU has 8 GB: never run the Ollama chat model and ComfyUI at the same time.

## Where we are (2026-10-06)
**The toolkit and the desktop app are done and tested.** Branch `claude/inspect-this-1wnu0l`.
- `um app` / `UniversalModder.exe` / `Universal Modder.cmd`: a portable desktop app (everything stays in this
  folder). Screens: Chat, Games, Art, Backups, Publish check, Settings.
  - Chat runs on the owner's Ollama. Models with tool calling (recommended: `qwen3:8b`, ~5.2 GB, context 8-16k)
    use it; models without it (Gemma 3, custom GGUF imports) get the tools as text instructions automatically.
  - Art reuses the owner's own ComfyUI workflow (Qwen-Image, set up on the Art screen with "Use my last ComfyUI
    image"), then `um sprite` turns results into game sprites. It unloads the chat model first.
  - The Windows `.exe` is built by the "windows app" GitHub Actions workflow (artifact
    "Universal Modder (Windows)").
- Heavy work (writing whole mods) is done by Claude Code on this PC, started with `Start Claude Code.cmd`.
  The app's local model is for scanning, backups, art and small edits.
- **One folder** (owner's choice, 2026-10-05): this clone is the whole workflow. The packaged app
  (`UniversalModder.exe`, `um.exe`, `_internal/`) sits in the clone's root, so it shares `data/` (settings) and
  `My Mods/` with `Universal Modder.cmd` (uv/Python in `.uv/`, `.venv/`); all of these are git-ignored. A Desktop
  shortcut points at the `.exe`. After app code changes, replace those three with a fresh "windows app" build
  (or use the `.cmd`, which always runs the current code). Mods Claude builds live in `mods/` and are committed. Local checks: `.uv\bin\uv.exe run --with pytest pytest -q tests` (with the
  launcher's `UV_*` variables); on Windows `tests/test_um.py` fails at collection (it calls `which`) and
  `um kb check` reports `INDEX.md` stale because of CRLF checkouts. Both pass in CI.

**Current project: Minecraft blocks inside State of Decay 2** (`mods/sod2-blocks`, paused 2026-10-06).
- The owner's goal is a game-to-game merge. On 2026-10-06 they switched the base game: **SoD2 is the base**, and
  Minecraft-style blocks (build and mine) are added to it with UE4SS. Solo/offline play only.
- **Working:** UE4SS runs in the Xbox app copy of SoD2, and F6/F5 place and break 1 m grid blocks where the camera
  aims (tested: a cube spawned and lit in game; the trace hits the landscape). The fixes SoD2's custom UE 4.13 needs
  (EngineVersionOverride 4.14, `VTableLayout.ini` with ProcessEvent at vtable slot 53, tracking
  `VanillaPlayerController_BP_C`, writing `Mobility` as a property, `LineTraceSingle_NEW`) are all in
  `mods/sod2-blocks/MODLOG.md`.
- **Installed now** in `C:\XboxGames\State of Decay 2\Content\StateOfDecay2\Binaries\Win64` (dwmapi.dll + ue4ss\,
  hot reload on). Develop with `install.ps1 -Sync` then Ctrl+R in game; read `...\Win64\ue4ss\UE4SS.log`.
  Remove with `uninstall.ps1`. If SoD2 won't start, restart the PC first: that fixed it once.
- **Paused:** SoD2 inside Minecraft (`mods/sod-in-minecraft`, v0.5.0). Real SoD2 guns (meshes, textures, sounds)
  render in Minecraft from a local pack; zombies use Minecraft bodies. Its MODLOG has everything.

## Next steps
1. The owner tests place/break: stacking, standing on blocks, whether zombies are blocked, F5. Then fix what's off
   (the aim point in third person).
2. Textures: try SoD2's own materials on the cubes (needs materials already in memory: `LoadAsset` fails because
   the asset registry is null). Minecraft textures need a cooked pak for UE 4.13/4.14.
3. Save the blocks per map (Lua `io` to a file in the mod folder) and rebuild them on load.
4. A block picker (types) and maybe mining by hitting.
5. Commit the pending `mods/sod-in-minecraft/tools/sod2_import.py` change (tuned hand/GUI transforms).
6. When it's solid: a field note (`um kb new`): this is the first UE4SS config for SoD2.

## Known issues in the toolkit (from the 2026-10-03 inspection, not fixed yet)
- `um scan` flags any game with "rust" in its name as an online game (substring match in `ONLINE_ONLY`).
- `um scan` route table matches substrings: GTA V Enhanced, Minecraft Dungeons, Slay the Spire 2 and Silksong get
  the wrong route.
- `um publish check` misses `.env.local` / `.env.production`.
- `um kb` prefers the plugin's copy of `knowledge/` over the current folder; `um kb pr` breaks with relative paths
  from a subfolder; `index.json` newline differs between `kb pr` and `kb index`.
- `um fal result` may build the wrong queue URL for endpoints with a sub-path; fal job submits retry on 5xx.
