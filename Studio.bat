@echo off
rem Double-click: open the documentary studio (http://localhost:5280/) for the last opened project.
rem Another project: Studio.bat <project-id>   (a folder in projects\)
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

rem Already running: just open the browser.
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:5280/api/etag) | Out-Null; exit 0 } catch { exit 1 }"
if %errorlevel%==0 (
  start "" http://localhost:5280/
  exit /b 0
)

if not exist ".venv\Scripts\python.exe" (
  echo Khong thay .venv - chay scripts\setup.ps1 truoc.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" studio\server.py %*
if errorlevel 1 pause
