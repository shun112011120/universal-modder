# Install SoDBlocks into State of Decay 2 (Xbox app copy), or just sync the mod files while developing.
#   powershell -NoProfile -ExecutionPolicy Bypass -File mods\sod2-blocks\install.ps1          # full install
#   powershell -NoProfile -ExecutionPolicy Bypass -File mods\sod2-blocks\install.ps1 -Sync    # copy our files only
# Full install: UE4SS (downloaded to data\tools\ue4ss by the agent, from github.com/UE4SS-RE/RE-UE4SS) goes next to
# StateOfDecay2-Win64-Shipping.exe as dwmapi.dll + ue4ss\, configured for SoD2 (EngineVersionOverride 4.14, hot reload),
# plus this mod's VTableLayout.ini and Mods\SoDBlocks. Every file it writes is listed in data\tools\ue4ss\INSTALLED-sod2.txt
# for uninstall.ps1. SoD2 must be closed for a full install. Play solo/offline with mods.
param([switch]$Sync)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$here = $PSScriptRoot
$ue4ss = Join-Path $repo "data\tools\ue4ss"
$win64 = "C:\XboxGames\State of Decay 2\Content\StateOfDecay2\Binaries\Win64"
$dst = Join-Path $win64 "ue4ss"
$list = Join-Path $ue4ss "INSTALLED-sod2.txt"

function Copy-Ours {
    New-Item -ItemType Directory -Force (Join-Path $dst "Mods\SoDBlocks\Scripts") | Out-Null
    Copy-Item (Join-Path $here "ue4ss\VTableLayout.ini") (Join-Path $dst "VTableLayout.ini") -Force
    Copy-Item (Join-Path $here "ue4ss\Mods\SoDBlocks\Scripts\main.lua") (Join-Path $dst "Mods\SoDBlocks\Scripts\main.lua") -Force
    Write-Output "copied VTableLayout.ini and SoDBlocks\Scripts\main.lua"
}

if ($Sync) {
    Copy-Ours
    Write-Output "synced; in game press Ctrl+R to reload mods"
    return
}

if (Get-Process -Name "StateOfDecay2-Win64-Shipping" -ErrorAction SilentlyContinue) { throw "close State of Decay 2 first" }
if (-not (Test-Path (Join-Path $ue4ss "dwmapi.dll"))) { throw "UE4SS isn't in $ue4ss yet (download it first)" }
if (Test-Path (Join-Path $win64 "dwmapi.dll")) { throw "dwmapi.dll is already in the game folder: run uninstall.ps1 first" }

Copy-Item (Join-Path $ue4ss "dwmapi.dll") $win64
Copy-Item (Join-Path $ue4ss "ue4ss") $win64 -Recurse
$ini = Join-Path $dst "UE4SS-settings.ini"
$t = [IO.File]::ReadAllText($ini)
$t = $t -replace "(?m)^MajorVersion =.*$", "MajorVersion = 4" -replace "(?m)^MinorVersion =.*$", "MinorVersion = 14" -replace "(?m)^EnableHotReloadSystem = .*$", "EnableHotReloadSystem = 1"
[IO.File]::WriteAllText($ini, $t)
Copy-Ours
$mods = Join-Path $dst "Mods\mods.txt"
if (-not (Select-String -Path $mods -Pattern "^SoDBlocks" -Quiet)) {
    $m = [IO.File]::ReadAllText($mods) -replace "(?m)^BPModLoaderMod : 1", "BPModLoaderMod : 1`r`nSoDBlocks : 1"
    [IO.File]::WriteAllText($mods, $m)
}
$installed = @((Join-Path $win64 "dwmapi.dll")) + (Get-ChildItem $dst -Recurse -File | ForEach-Object { $_.FullName })
$installed | Set-Content -Encoding utf8 $list
Write-Output ("installed {0} files (list: {1})" -f $installed.Count, $list)
