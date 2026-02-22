# DeepPrime Workspace

This folder is the new install-oriented home for the DeepPrime program.

## Purpose
- keep runtime app code and distribution assets separate
- prepare clean packaging for one-click installer delivery
- separate binaries, databases, config, logs, and release artifacts

## Top-Level Layout
- `app/` application source and launchers
- `tools/` third-party executables and helper scripts
- `databases/` indexed sequence databases
- `config/` shipped/default configuration files
- `runtime/` writable runtime state (`logs/`, `tmp/`, `cache/`)
- `docs/` architecture and packaging documentation
- `release/` build outputs (installer and manifests)

See `docs/FOLDER_STRUCTURE.md` for details and migration mapping.

## Asset Staging (Installer Prep)
- Script: `DeepPrime/tools/scripts/stage_assets.py`
- Wrapper: `DeepPrime/tools/scripts/stage_assets.ps1`

Examples:
```powershell
# Preview without writing
& "C:\Users\svenr\anaconda3\python.exe" "C:\Users\svenr\Documents\DeepPrimeRL\python_port\DeepPrime\tools\scripts\stage_assets.py" --dry-run

# Stage assets with hardlinks (fast, same disk)
& "C:\Users\svenr\anaconda3\python.exe" "C:\Users\svenr\Documents\DeepPrimeRL\python_port\DeepPrime\tools\scripts\stage_assets.py" --mode hardlink
```

Manifest output:
- `DeepPrime/release/asset_manifest.json`

## Installer Build
- Installer guide: `DeepPrime/docs/INSTALLER_BUILD.md`
- Inno script: `DeepPrime/release/installer/DeepPrime.iss`
- Build helper: `DeepPrime/release/installer/build_installer.ps1`

