@echo off
rem Double-click: gets the latest files, installs Claude Code on first run (asks first), and starts a
rem Claude Code session in this folder that picks up where the last one left off (START_HERE.md).
setlocal
rem don't let a PowerShell 7 parent leak its module path into Windows PowerShell
set "PSModulePath="
title Universal Modder - Claude Code
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup\start-claude.ps1"
if errorlevel 1 (
  echo.
  if not defined CI pause
)
