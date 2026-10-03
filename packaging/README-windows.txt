Universal Modder for Windows
============================

1. Double-click UniversalModder.exe. The app opens in its own window (it uses Microsoft Edge, which Windows
   already has). Closing the window quits the app.
2. For the AI chat, install Ollama from https://ollama.com and pull a model that supports tools, e.g.
       ollama pull qwen3-coder      (strong GPU, ~24 GB of VRAM)
       ollama pull qwen3:8b         (smaller GPUs)
   Then pick the model in Settings.
3. The Games, Backups and Publish check screens work without Ollama.

Windows may warn that the app is from an unknown publisher (it isn't code-signed): click "More info", then
"Run anyway". Keep this whole folder together; um.exe is the command-line toolkit the app uses.

Settings and backups are stored in %USERPROFILE%\.universal-modder. New mod files go to your workspace folder
(Documents\Universal Modder unless you change it in Settings).
