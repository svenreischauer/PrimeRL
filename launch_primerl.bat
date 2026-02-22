@echo off
setlocal
set "ROOT=%~dp0"

set "PYW=%ROOT%python\pythonw.exe"
if not exist "%PYW%" set "PYW=%ROOT%python\python.exe"

if exist "%PYW%" (
  start "" "%PYW%" "%ROOT%run_gui.py"
  exit /b 0
)

where pythonw >nul 2>nul
if %ERRORLEVEL%==0 (
  start "" pythonw "%ROOT%run_gui.py"
  exit /b 0
)

echo No pythonw launcher found. Falling back to python (console window may appear).
start "" python "%ROOT%run_gui.py"
exit /b 0
