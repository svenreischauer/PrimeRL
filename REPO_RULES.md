# Repository Rules (PrimeRL)

These rules define what is allowed in Git and what must stay local.

## 1) Track in Git
- Source code: `src/`, `PrimeRL/app/src/`
- Tests: `tests/`
- Documentation: `docs/`, `README.md`, `TODO.md`
- Build/setup scripts: `release/scripts/`, `tools/scripts/`
- Launchers and config templates (for example `*.example.json`, `.gitkeep`)
- Third-party notices/licenses (text/docs only)

## 2) Never Track in Git
- Downloaded transcriptome databases and indexes
  - `PrimeRL/databases/`
- Binary tool payloads and bundled executables
  - `PrimeRL/tools/bin/`
- Runtime state/output
  - `PrimeRL/runtime/logs/`
  - `PrimeRL/runtime/tmp/`
  - `PrimeRL/runtime/cache/`
  - `PrimeRL/runtime/exports/`
  - `PrimeRL/runtime/gui_settings.json`
- Built release artifacts and packaging outputs
  - `release/PrimeRL_*_exe_win64_nodb/`
  - `release/PrimeRL_*_msi_win64/`
  - `release/PrimeRL_*_portable*/`
  - `release/*.zip`
  - `releases/`

## 3) Distribution Model
- GitHub repository: source-only.
- Deliverables (`.msi`, `.exe`, `.zip`): publish as Release assets, not Git-tracked files.
- Databases/indexes: download/index locally at runtime or via setup workflow.

## 4) Commit Hygiene
- Before commit:
  - `git status`
  - verify no runtime/binary/database files are staged.
- Keep commits focused and readable.
- Do not commit machine-specific local settings.

## 5) If a Large/Binary File Was Accidentally Committed
- Remove it from current tracking (`git rm --cached ...`) and commit.
- If needed, clean history and force-push only with explicit team agreement.
