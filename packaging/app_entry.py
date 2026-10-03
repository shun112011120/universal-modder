"""Entry point of the packaged app: UniversalModder.exe opens the app window, um.exe (same folder) is the CLI
that the app runs its tools with. Built by packaging/universal-modder.spec."""
import sys
from pathlib import Path

from um.cli import main

if Path(sys.executable).stem.lower() == "um":
    main(sys.argv[1:])
else:
    main(["app", *sys.argv[1:]])
