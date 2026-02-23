# PrimeRL

PrimeRL is a qPCR primer design workspace with a Tkinter/ttkbootstrap GUI and
local tooling for primer design and specificity checks.

## Project Layout
- Application code: `src/primerl`
- GUI launcher: `run_gui.py`
- Tests: `tests`
- Runtime structure (local): `PrimeRL/`
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

## macOS Apple Silicon
Quick launcher:
```bash
./start_primerl.sh
```

Finder launcher:
```bash
./start_primerl.command
```

What the launcher does:
- creates `.venv` with `--system-site-packages` (if missing)
- installs `ttkbootstrap` and `openpyxl` into that venv
- warns if `spidey` is not available
- starts `run_gui.py`

Bootstrap/check script:
```bash
./tools/scripts/bootstrap_macos_apple_silicon.sh
```

The bootstrap script creates local runtime directories and reports missing external tools.
It does not download or commit binaries.
