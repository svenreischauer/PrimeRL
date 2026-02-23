# PrimeRL Installer Build

This folder contains a baseline Inno Setup installer for PrimeRL.

## Files
- `PrimeRL/release/installer/PrimeRL.iss`
- `PrimeRL/release/installer/build_installer.ps1`

## What gets installed
- PrimeRL app launcher and source (`app/run_gui.py`, `src/PrimeRL`)
- tool binaries (`tools/bin`)
- databases (`databases/ensembl`, `databases/refseq`)
- docs/config/runtime folder structure

## Build steps
1. Install Inno Setup 6 (`ISCC.exe`).
2. Run:
   ```powershell
   & "C:\Users\svenr\Documents\PrimeRL\python_port\PrimeRL\release\installer\build_installer.ps1" -Profile core
   ```
3. Output installer:
   - `PrimeRL/release/installer/dist/PrimeRLSetup_0.2.0_core.exe`

## Installer profiles
- `core` (recommended for iteration)
  - excludes `databases/*`
  - much faster build and smaller installer
- `performance` (recommended deployment profile)
  - excludes `databases/*`
  - compiles Primer3 tools from source for Intel Haswell+:
    - `primer3_core_v2.6.1_AVX2_FMA3.exe`
    - `ntthal_v2.6.1_AVX2_FMA3.exe`
    - `oligotm_v2.6.1_AVX2_FMA3.exe`
  - optimization flags:
    - `-O3 -march=haswell -mtune=haswell -fomit-frame-pointer -DNDEBUG -s`
  - stages `Spidey_AVX2_FMA3.exe` from `wip` when available, otherwise falls back to `Spidey.exe`
- `full`
  - includes staged `databases/ensembl` and `databases/refseq`
  - larger installer and longer build time

Build full installer:
```powershell
& "C:\Users\svenr\Documents\PrimeRL\python_port\PrimeRL\release\installer\build_installer.ps1" -Profile full
```

Build performance installer:
```powershell
& "C:\Users\svenr\Documents\PrimeRL\python_port\PrimeRL\release\installer\build_installer.ps1" -Profile performance
```

## Runtime note
- Launcher: `launch_PrimeRL.bat`
- It first tries bundled Python in `app/python/` (if present), then falls back to `pythonw/pyw/python` on PATH.
- If no Python runtime is found, it shows an error and exits.

## Next hardening tasks
1. Bundle embeddable Python into `app/python` for fully self-contained installs.
2. Add app icon + version metadata.
3. Add CI task that builds and hashes performance binaries before installer compile.


