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

## Where we are (2026-10-05)
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
- **One folder** (owner's choice, 2026-10-05): this clone is the whole workflow. The owner runs the app with
  `Universal Modder.cmd` from here (uv, Python and libraries in `.uv/` and `.venv/`, settings in `data/`, app
  workspace in `My Mods/`, all git-ignored); the separate `.exe` folder was retired. Mods Claude builds live in
  `mods/` and are committed. Local checks: `.uv\bin\uv.exe run --with pytest pytest -q tests` (with the
  launcher's `UV_*` variables); on Windows `tests/test_um.py` fails at collection (it calls `which`) and
  `um kb check` reports `INDEX.md` stale because of CRLF checkouts. Both pass in CI.

**Current project: State of Decay 2 inside Minecraft** (v0.1.0 written, not tested in game yet).
- Route: a Minecraft **Java** mod (Fabric), pattern 1 of `skills/mashup-mods` ("port the content"): State of
  Decay 2's ideas rebuilt in Minecraft from scratch. Never copy State of Decay files, models, textures or sounds.
- Code: `mods/sod-in-minecraft/` (mod id `sodcraft`, Minecraft **26.3**, Fabric, JDK 25). Its `MODLOG.md` has
  the versions, what's built and the ideas queue. The "sodcraft mod" workflow builds the jar (artifact
  `sodcraft-mod`), so the PC needs no JDK or Gradle.
- Built: **Plague Heart** block (zombie waves at night while a player is near, defenders when hit, stops when
  destroyed) and **Screamer** zombie (screams when it sees you: calls zombies within 40 blocks, staggers you).
  Placeholder textures drawn by `mods/sod-in-minecraft/tools/make_placeholder_textures.py`.
- The owner's PC (2026-10-03): Minecraft Launcher (Xbox app) + Bedrock installed; Java Edition never launched,
  no Fabric, no Java worlds. Claude Code runs on this PC through the Claude desktop app (Code tab, local session).

## Next steps
1. Get the "sodcraft mod" workflow green (read its log, fix compile errors).
2. Owner: confirm they own Java Edition, launch **26.3** once from the launcher. Then (ask first) install Fabric
   Loader 0.19.5 for 26.3 (fabric-installer; with the Xbox launcher add the profile to `launcher_profiles.json` by
   hand, with its own `gameDir`; see `knowledge/games/gta-v/minecraft-passthrough.md` gotcha 3) and put Fabric
   API 0.161.0+26.3 and the sodcraft jar in that game dir's `mods\`.
3. Back up worlds before modded launches: `um backup create <gameDir>\saves --name minecraft-saves`.
4. Test in game (steps in `mods/sod-in-minecraft/MODLOG.md`), read `<gameDir>\logs\latest.log`, fix.
5. ComfyUI textures (Art screen), then `um sprite pixelate <png> <out> --size 16x16 --colors 16`.
6. Next freaks: Bloater, Feral, Juggernaut; then blood plague.
7. When it works: `um publish check`, a field note with `um kb new` (ask before a PR).

## Known issues in the toolkit (from the 2026-10-03 inspection, not fixed yet)
- `um scan` flags any game with "rust" in its name as an online game (substring match in `ONLINE_ONLY`).
- `um scan` route table matches substrings: GTA V Enhanced, Minecraft Dungeons, Slay the Spire 2 and Silksong get
  the wrong route.
- `um publish check` misses `.env.local` / `.env.production`.
- `um kb` prefers the plugin's copy of `knowledge/` over the current folder; `um kb pr` breaks with relative paths
  from a subfolder; `index.json` newline differs between `kb pr` and `kb index`.
- `um fal result` may build the wrong queue URL for endpoints with a sub-path; fal job submits retry on 5xx.
