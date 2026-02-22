# primerl Runtime

This folder contains the active primerl Python runtime.

## Source of Truth
- Active package: `src/primerl`
- GUI launcher: `run_gui.py`
- Tests: `tests/`
- Runtime app assets: auto-detected runtime root with `tools/`, `databases/`, and `runtime/`

## Workspace Scope Lock
- All active work is limited to `01_DeepPrime_Runtime`.
- Do not edit sibling folders in `..\` (including `..\Verdent` and `..\Primer3`).
- Treat this folder as the only writable project scope for primerl development.

## Cleanup State (2026-02-16)
- Handoff/session docs moved to `docs/handoff/`.
- `gui.py` backups moved to `docs/archive/source_backups/`.
- GUI launch logs are written under the detected runtime root at `runtime/logs/`.
- Build/cache directories are intended to stay untracked.

## Run GUI
```powershell
& "C:\Users\svenr\anaconda3\python.exe" ".\run_gui.py"
```

## Run Tests
```powershell
$env:PYTHONPATH = ".\src"
& "C:\Users\svenr\anaconda3\python.exe" -m unittest discover -s .\tests -v
```

## Build Primer3 Clang Profiles
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_primer3_clang_profiles.ps1
```
- Source expected at: `third_party/primer3_src`
- Output written to:
  - `DeepPrime/tools/bin/clang_profiles/znver2`
  - `DeepPrime/tools/bin/clang_profiles/znver4`
  - `DeepPrime/tools/bin/clang_profiles/x86_64_v3`

