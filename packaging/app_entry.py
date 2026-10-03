"""Entry point of the packaged app: UniversalModder.exe opens the app window, um.exe (same folder) is the CLI
that the app runs its tools with. Built by packaging/universal-modder.spec."""
import os
import sys
from pathlib import Path

# portable: settings, backups and mods stay in this folder (um/common.py portable_root)
os.environ.setdefault("UM_PORTABLE", str(Path(sys.executable).resolve().parent))

from um.cli import main  # noqa: E402

if Path(sys.executable).stem.lower() == "um":
    main(sys.argv[1:])
else:
    main(["app", *sys.argv[1:]])
