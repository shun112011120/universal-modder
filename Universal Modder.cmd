@echo off
rem Double-click to open the Universal Modder app (Windows).
rem Needs uv (https://docs.astral.sh/uv/, recommended) or Python 3.10+ with pillow, numpy and pyyaml.
rem The AI chat also needs Ollama (https://ollama.com) with a model that supports tools.
setlocal
set "ROOT=%~dp0"
title Universal Modder
echo Starting Universal Modder... (this window closes when you close the app)
where uv >nul 2>nul && goto :uv
where py >nul 2>nul && goto :py
set "PY=python"
goto :run
:uv
uv run --quiet --project "%ROOT%." python -m um app %*
goto :end
:py
set "PY=py -3"
:run
set "PYTHONPATH=%ROOT%.;%PYTHONPATH%"
%PY% -m um app %*
:end
if errorlevel 1 (
  echo.
  echo Universal Modder stopped with an error. Install uv from https://docs.astral.sh/uv/ and try again.
  pause
)
