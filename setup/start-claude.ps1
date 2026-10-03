# Start a Claude Code session in this folder that picks up where the last one left off (START_HERE.md).
# First run: offers to install Claude Code and puts it on PATH. Started by "Start Claude Code.cmd".
# Windows PowerShell 5.1 compatible.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

function Ask([string]$Question) {
    $a = Read-Host "$Question [y/N]"
    return $a -match '^(y|yes)$'
}

Write-Host ""
Write-Host "== Universal Modder: starting Claude Code ==" -ForegroundColor Green
Write-Host "Folder: $Root"

# 1. Latest files from GitHub (skipped quietly if git or the network isn't there)
if (Get-Command git -ErrorAction SilentlyContinue) {
    if (Test-Path -LiteralPath (Join-Path $Root ".git")) {
        Write-Host "Getting the latest files..."
        # git writes progress to stderr; Windows PowerShell would turn that into errors under "Stop"
        $ErrorActionPreference = "Continue"
        $out = & git -C $Root pull --ff-only 2>&1
        $ErrorActionPreference = "Stop"
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Couldn't update (you may have local changes). Carrying on with the files you have."
            Write-Host ($out | Out-String)
        } else {
            Write-Host ($out | Select-Object -Last 1)
        }
    }
} else {
    Write-Warning "Git isn't installed, so this folder can't update itself. Get it from https://git-scm.com"
}

# 2. Claude Code: find it, or offer to install it
$Bin = Join-Path $env:USERPROFILE ".local\bin"
$Exe = Join-Path $Bin "claude.exe"
$Claude = $null
$cmd = Get-Command claude -ErrorAction SilentlyContinue
if ($cmd) { $Claude = $cmd.Source }
elseif (Test-Path -LiteralPath $Exe) { $Claude = $Exe }

if (-not $Claude) {
    Write-Host ""
    Write-Host "Claude Code isn't installed yet. It comes from Anthropic's official installer (https://claude.ai/install.ps1)"
    Write-Host "and goes into $Bin. You sign in with your Claude account the first time."
    if (-not (Ask "Install Claude Code now?")) {
        Write-Host "OK, nothing installed. Alternative: the Claude desktop app (claude.ai/download), Code tab, this folder."
        exit 1
    }
    Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression
    if (Test-Path -LiteralPath $Exe) { $Claude = $Exe }
    else {
        $cmd = Get-Command claude -ErrorAction SilentlyContinue
        if ($cmd) { $Claude = $cmd.Source }
    }
    if (-not $Claude) {
        Write-Warning "The installer finished but claude.exe wasn't found. Copy the messages above and ask for help."
        exit 1
    }
}

# 3. Make plain `claude` work in new terminals ("is not recognized" fix)
if ($Claude -eq $Exe) {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $userPath) { $userPath = "" }
    $parts = @($userPath -split ";" | Where-Object { $_ -ne "" })
    if ($parts -notcontains $Bin) {
        [Environment]::SetEnvironmentVariable("Path", (($parts + $Bin) -join ";"), "User")
        Write-Host "Added $Bin to your PATH, so 'claude' works in new terminals too."
    }
    if (($env:Path -split ";") -notcontains $Bin) { $env:Path = "$env:Path;$Bin" }
}

# 4. Personal notes
if (-not (Test-Path -LiteralPath (Join-Path $Root "SETUP_SUMMARY.md"))) {
    Write-Host ""
    Write-Host "Tip: copy your SETUP_SUMMARY.md (PC specs, models, ComfyUI) into this folder so Claude knows your setup." -ForegroundColor Yellow
}

# 5. Go
Write-Host ""
Write-Host "Starting Claude Code. Type /exit (or close this window) when you're done." -ForegroundColor Green
$first = "Read START_HERE.md, and SETUP_SUMMARY.md if it exists. Tell me in a few lines where we are and what's next, " +
         "then ask me before starting the next step."
& $Claude $first
