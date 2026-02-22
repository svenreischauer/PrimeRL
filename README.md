# PrimeRL

PrimeRL is a qPCR primer design workspace with a Tkinter/ttkbootstrap GUI and
local tooling for primer design and specificity checks.

## Project Layout
- Application code: `src/primerl`
- GUI launcher: `run_gui.py`
- Tests: `tests`
- Runtime structure (local): `DeepPrime/`
- Build scripts: `release/scripts`

## Repository Rules
This repository follows a strict source-only policy.

See: `REPO_RULES.md`

In short:
- Track source code, docs, tests, scripts, and lightweight templates.
- Do not track local databases, binary tool payloads, runtime outputs, or built installers/zip artifacts.

## Local Development
Run GUI:
```powershell
python .\run_gui.py
```

Run tests:
```powershell
$env:PYTHONPATH = ".\src"
python -m unittest discover -s .\tests -v
```

Build Windows artifacts (local only):
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\scripts\build_exe.ps1 -Version 1.1 -Clean
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\scripts\build_msi.ps1 -Version 1.1.0 -Clean
```
