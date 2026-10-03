Universal Modder for Windows
============================

Everything lives in this one folder. Put it on your Desktop (or anywhere) and keep it together:
  UniversalModder.exe   the app - double-click it
  um.exe, _internal     the toolkit the app runs on (don't move these out)
  data                  made on first run: settings, save backups, the app window's browser data
  My Mods               made on first run: where the AI writes your mod files

1. Double-click UniversalModder.exe. The app opens in its own window (it uses Microsoft Edge, which Windows
   already has). Closing the window quits the app.
2. For the AI chat, install Ollama from https://ollama.com and pull a model that supports tools, e.g.
       ollama pull qwen3-coder      (strong GPU, ~24 GB of VRAM)
       ollama pull qwen3:8b         (smaller GPUs)
   Then pick the model in Settings. Ollama is its own program, so it and its models are installed outside
   this folder.
3. The Games, Backups and Publish check screens work without Ollama.

Windows may warn that the app is from an unknown publisher (it isn't code-signed): click "More info", then
"Run anyway".

To move the app, move the whole folder. To uninstall, delete the folder (copy "My Mods" out first if you
want to keep your mods).
