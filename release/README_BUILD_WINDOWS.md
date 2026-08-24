# PrimeRL Windows Packaging

This folder contains build scripts for a Windows executable (`.exe`) and MSI installer.

## Output layout

- EXE payload: `release/PrimeRL_1.3.1_exe_win64_nodb/dist/PrimeRL/PrimeRL.exe`
- MSI package: `release/PrimeRL_1.3.1_msi_win64/PrimeRL_1.3.1_win64.msi`

## Runtime data location

PrimeRL now separates read-only app resources from mutable runtime data when running as a frozen app (`sys.frozen`).

- App binaries/resources: installation directory (typically `Program Files\PrimeRL`)
- Mutable data (runtime settings/logs/exports and downloaded transcriptome DBs):
  - `%LOCALAPPDATA%\PrimeRL\runtime`
  - `%LOCALAPPDATA%\PrimeRL\databases`

Override data root (advanced): set environment variable `PRIMERL_DATA_DIR`.

## Build .exe (PyInstaller)

1. Install the tested build dependencies:
   - `python -m pip install ".[build]"`
2. Build:
   - `powershell -ExecutionPolicy Bypass -File release/scripts/build_exe.ps1 -Version 1.3.1 -Clean`

The build uses assets from the existing no-database portable bundle at:
`release/PrimeRL_1.3.1_portable_win64_nodb/PrimeRL 1.3.1`.

## Build MSI (WiX CLI v7; v6 remains supported)

Prerequisite: WiX CLI installed.
- `winget install --id WiXToolset.WiXCLI -e`

1. Build MSI from existing EXE payload:
   - `powershell -ExecutionPolicy Bypass -File release/scripts/build_msi.ps1 -Version 1.3.1 -Clean`
2. Or build EXE first, then MSI in one call:
   - `powershell -ExecutionPolicy Bypass -File release/scripts/build_msi.ps1 -Version 1.3.1 -BuildExe -Clean`

The MSI uses `WixUI_InstallDir`, so users can choose install location (default `Program Files`) and explicitly choose whether to create a desktop shortcut (enabled by default).
