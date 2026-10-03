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

## Where we are (2026-10-03)
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

**Current project: State of Decay 2 inside Minecraft** (decided, not started).
- Route: a Minecraft **Java** mod (Fabric), pattern 1 of `skills/mashup-mods` ("port the content"): State of
  Decay 2's ideas rebuilt in Minecraft from scratch, with new art from ComfyUI. Never copy State of Decay files,
  models, textures or sounds.
- First slice: a **Plague Heart** block that spawns zombie waves around it at night until destroyed, and a
  **Screamer** zombie that calls nearby zombies when it sees the player. 16x16 pixel-art textures.
- Later ideas: freak zombies (Bloater gas cloud, Juggernaut), survivors with traits and morale, an outpost /
  base-building system, scavenging rucksacks, plague sickness.
- Unknown yet: the owner's Minecraft Java version (launcher, next to Play), whether Fabric is installed, and
  whether they also have Bedrock (it can't take this mod).

## Next steps
1. `um scan --list`, then `um scan "State of Decay 2"` and find Minecraft (Java installs live in
   `%APPDATA%\.minecraft`; the scanner may not list it because it isn't a Steam/Epic/Xbox game).
2. Ask the owner for the Minecraft Java version; check `%APPDATA%\.minecraft\versions` and `mods`.
3. Back up the worlds: `um backup create "%APPDATA%\.minecraft\saves" --name minecraft-saves`.
4. List what's needed and ask before installing: a JDK 21 (or what that Minecraft version needs), the Fabric
   installer and Fabric API, and the first Gradle build's downloads (about 1-2 GB, one time).
5. Create the mod in `My Mods\sod-in-minecraft\` (from the Fabric example mod for that version), with a
   `MODLOG.md`. Build the Plague Heart + Screamer, test in game, read `logs\latest.log` for errors.
6. Make the textures with ComfyUI (Art screen or the app's `generate_image` tool), then
   `um sprite pixelate <png> <out> --size 16x16 --colors 16`.
7. When it works: `um publish check` on the mod folder, and a field note with `um kb new` (ask before a PR).

## Known issues in the toolkit (from the 2026-10-03 inspection, not fixed yet)
- `um scan` flags any game with "rust" in its name as an online game (substring match in `ONLINE_ONLY`).
- `um scan` route table matches substrings: GTA V Enhanced, Minecraft Dungeons, Slay the Spire 2 and Silksong get
  the wrong route.
- `um publish check` misses `.env.local` / `.env.production`.
- `um kb` prefers the plugin's copy of `knowledge/` over the current folder; `um kb pr` breaks with relative paths
  from a subfolder; `index.json` newline differs between `kb pr` and `kb index`.
- `um fal result` may build the wrong queue URL for endpoints with a sub-path; fal job submits retry on 5xx.
