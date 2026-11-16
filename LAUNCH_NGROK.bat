@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

if exist ".env" (
  for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if not "%%A"=="" set "%%A=%%B"
  )
)

set "PY_EXE="
if exist ".venv\Scripts\python.exe" (
  set "PY_EXE=.venv\Scripts\python.exe"
) else (
  python -c "import streamlit" >nul 2>&1
  if not errorlevel 1 (
    set "PY_EXE=python"
  ) else (
    echo [SETUP] Creating .venv and installing requirements...
    python -m venv .venv
    set "PY_EXE=.venv\Scripts\python.exe"
    "%PY_EXE%" -m pip install -r requirements.txt
  )
)

"%PY_EXE%" "%~dp0ngrok_launch.py"
pause
