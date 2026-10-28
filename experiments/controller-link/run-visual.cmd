@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" launch_visual.py %*
if errorlevel 1 goto failed
exit /b 0
:failed
echo Could not launch. Check that Python includes Tkinter and see the error above.
pause
exit /b 1
