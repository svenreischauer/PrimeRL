# Latest Working State

Date: 2026-02-16
Workspace: `C:\Users\svenr\Documents\HiDrive\Cortex Workspace\DeepPrimeRL\DeepPrime`

## Canonical Runtime
- Root: `01_DeepPrime_Runtime`
- Code: `01_DeepPrime_Runtime\src\deepprimerl`
- Launcher: `01_DeepPrime_Runtime\run_gui.py`
- Unit tests: `01_DeepPrime_Runtime\tests`
- Scope lock: only this runtime folder is in active development scope.

## Validation
- Test suite executed with `C:\Users\svenr\anaconda3\python.exe`
- Result: 54 tests passed (`OK`)
- Command:
  - `$env:PYTHONPATH='...\01_DeepPrime_Runtime\src'; & 'C:\Users\svenr\anaconda3\python.exe' -m unittest discover -s '...\01_DeepPrime_Runtime\tests' -v`

## Cleanup Actions Applied
- Moved session docs from runtime root to `docs\handoff\`.
- Moved `gui.py` backup variants to `docs\archive\source_backups\`.
- Moved GUI launch logs to `DeepPrime\runtime\logs\`.
- Removed Python cache directories (`__pycache__`).

## Non-Goals in This Pass
- `Verdent/` left untouched (separate project/repo).
- `Primer3/` assets left untouched.
- No functional code changes to `deepprimerl`.

## Operational Rule Going Forward
- All agent-driven changes must stay inside `01_DeepPrime_Runtime`.
- Sibling folders in `DeepPrime` root are out of scope unless explicitly requested.

