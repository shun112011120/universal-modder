@echo off
rem Double-click to open the Universal Modder app (Windows). Portable: everything it downloads or makes
rem (uv, Python, libraries, settings, backups, your mods) stays inside this folder.
rem The AI chat also needs Ollama (https://ollama.com) with a model that supports tools.
setlocal
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "UM_PORTABLE=%ROOT%"
set "UV_CACHE_DIR=%ROOT%\.uv\cache"
set "UV_PYTHON_INSTALL_DIR=%ROOT%\.uv\python"
set "UV_PYTHON_PREFERENCE=only-managed"
set "UV_PROJECT_ENVIRONMENT=%ROOT%\.venv"
set "UV=%ROOT%\.uv\bin\uv.exe"
title Universal Modder
if exist "%UV%" goto :run
echo First run: downloading uv (the Python manager) into this folder...
rem an "unmanaged" install: no PATH changes, no install receipt, nothing outside this folder
set "UV_UNMANAGED_INSTALL=%ROOT%\.uv\bin"
rem started from PowerShell 7, Windows PowerShell would inherit 7's module path and fail to load its own modules
set "PSModulePath="
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
if not exist "%UV%" (
  echo Could not download uv. Check your internet connection and try again.
  if not defined CI pause
  exit /b 1
)
echo First run: setting up Python and the app's libraries (a minute or two)...
:run
echo Starting Universal Modder... (this window closes when you close the app)
"%UV%" run --quiet --project "%ROOT%" python -m um app %*
set "CODE=%errorlevel%"
if not "%CODE%"=="0" (
  echo.
  echo Universal Modder stopped with an error ^(see above^).
  if not defined CI pause
)
exit /b %CODE%
