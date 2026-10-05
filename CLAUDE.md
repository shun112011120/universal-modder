@AGENTS.md

## Claude Code specifics
- At the start of a session, read `START_HERE.md` (where the current project is) and `SETUP_SUMMARY.md`
  if it exists (the owner's PC; git-ignored, never commit it). Update `START_HERE.md` before you finish.
- `Start Claude Code.cmd` (Windows) installs Claude Code if needed and starts a session that does this.
- Installed as a plugin, the skills are namespaced (`/universal-modder:mod-any-game`), the fal MCP server comes
  from `.mcp.json` (needs `FAL_KEY` in the environment), and a SessionStart hook puts `um` on PATH.
- In a clone, `.claude/settings.json` adds the same PATH hook, and `.claude/skills` is a copy of `skills/`.
