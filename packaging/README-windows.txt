Universal Modder for Windows
============================

Everything lives in this one folder. Put it on your Desktop (or anywhere) and keep it together:
  UniversalModder.exe   the app - double-click it
  um.exe, _internal     the toolkit the app runs on (don't move these out)
  data                  made on first run: settings, save backups, the app window's browser data
  My Mods               made on first run: where the AI writes your mod files

1. Double-click UniversalModder.exe. The app opens in its own window (it uses Microsoft Edge, which Windows
   already has). Closing the window quits the app.
2. For the AI chat, install Ollama from https://ollama.com and pick any of its models in Settings. Models
   with tool calling (qwen3, llama3.1, ...) are the most reliable; others, like Gemma 3 or your own GGUF
   imports, get the tools as text instructions automatically. On an 8 GB GPU set Context size to 8k.
   Ollama is its own program, so it and its models are installed outside this folder.
3. For art, start your ComfyUI, make one image the way you normally do, then on the Art screen click
   "Use my last ComfyUI image". The app reuses that workflow and only changes the prompt, size and seed.
4. The Games, Backups and Publish check screens work without Ollama or ComfyUI.

Windows may warn that the app is from an unknown publisher (it isn't code-signed): click "More info", then
"Run anyway".

To move the app, move the whole folder. To uninstall, delete the folder (copy "My Mods" out first if you
want to keep your mods).
