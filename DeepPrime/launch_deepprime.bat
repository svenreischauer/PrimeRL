@echo off
setlocal

set "ROOT=%~dp0"
set "APP=%ROOT%app"
set "SCRIPT=%APP%\run_gui.py"

if not exist "%SCRIPT%" (
  echo DeepPrime launch script not found: "%SCRIPT%"
  pause
  exit /b 2
)

set "PYW="
if exist "%APP%\python\pythonw.exe" set "PYW=%APP%\python\pythonw.exe"
if not defined PYW if exist "%APP%\python\python.exe" set "PYW=%APP%\python\python.exe"

if not defined PYW (
  for %%P in (pythonw.exe pyw.exe python.exe) do (
    where %%P >nul 2>&1
    if not errorlevel 1 (
      set "PYW=%%P"
      goto :launch
    )
  )
)

if not defined PYW (
  echo Could not find a Python runtime.
  echo Install Python 3.11+ or bundle embeddable Python at: "%APP%\python"
  pause
  exit /b 3
)

:launch
start "" "%PYW%" "%SCRIPT%"
exit /b 0
