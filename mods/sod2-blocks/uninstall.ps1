# Remove UE4SS + SoDBlocks from State of Decay 2: deletes dwmapi.dll and the ue4ss folder next to the game's exe
# (nothing else; the game's own files are untouched). SoD2 must be closed.
#   powershell -NoProfile -ExecutionPolicy Bypass -File mods\sod2-blocks\uninstall.ps1
$ErrorActionPreference = "Stop"
$win64 = "C:\XboxGames\State of Decay 2\Content\StateOfDecay2\Binaries\Win64"
if (Get-Process -Name "StateOfDecay2-Win64-Shipping" -ErrorAction SilentlyContinue) { throw "close State of Decay 2 first" }
foreach ($p in @((Join-Path $win64 "dwmapi.dll"), (Join-Path $win64 "dwmapi.dll.disabled"), (Join-Path $win64 "ue4ss"))) {
    if (Test-Path $p) { Remove-Item $p -Recurse -Force; Write-Output "removed $p" }
}
Write-Output "State of Decay 2 is back to its own files:"
Get-ChildItem $win64 | Select-Object -ExpandProperty Name
