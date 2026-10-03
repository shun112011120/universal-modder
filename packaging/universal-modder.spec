# PyInstaller spec for the Windows app: one folder with UniversalModder.exe (the app, no console window) and
# um.exe (the CLI the app calls for its tools), sharing one Python runtime.
#   uv run --with pyinstaller pyinstaller --noconfirm packaging/universal-modder.spec   ->  dist/UniversalModder/
# .github/workflows/windows-app.yml builds it on every change and uploads it as an artifact.
from pathlib import Path

ROOT = Path(SPECPATH).parent
datas = [(str(ROOT / "um" / d), f"um/{d}") for d in ("app_ui", "fonts", "ps1", "blender")]
datas += [(str(ROOT / "skills"), "skills"), (str(ROOT / "knowledge"), "knowledge")]
groups = ["scan", "fal", "sprite", "render3d", "video", "win", "backup", "publish", "kb", "app"]   # imported by name in um/cli.py

a = Analysis([str(ROOT / "packaging" / "app_entry.py")], pathex=[str(ROOT)], datas=datas,
             hiddenimports=[f"um.{g}" for g in groups] + ["yaml"], excludes=["pytest"])
pyz = PYZ(a.pure)
icon = str(ROOT / "packaging" / "icon.ico")
app = EXE(pyz, a.scripts, [], exclude_binaries=True, name="UniversalModder", console=False, icon=icon)
cli = EXE(pyz, a.scripts, [], exclude_binaries=True, name="um", console=True, icon=icon)
COLLECT(app, cli, a.binaries, a.datas, name="UniversalModder")
