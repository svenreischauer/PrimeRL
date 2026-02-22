# PrimeRL Folder Structure

## Proposed Runtime/Distribution Structure
- `PrimeRL/app/src/PrimeRL/`
  - future Python package root for GUI and app modules
- `PrimeRL/tools/bin/`
  - external binaries: `primer3_core`, `ntthal`, `oligotm`, `Spidey`, `mfeprimer`
- `PrimeRL/tools/scripts/`
  - maintenance/indexing scripts
- `PrimeRL/databases/ensembl/`
  - Ensembl FASTA + `.primerqc` index files
- `PrimeRL/databases/refseq/`
  - RefSeq FASTA + `.primerqc` index files
- `PrimeRL/config/`
  - default app settings, path presets
- `PrimeRL/runtime/logs/`
  - app logs
- `PrimeRL/runtime/tmp/`
  - temporary files
- `PrimeRL/runtime/cache/`
  - cached API/analysis artifacts
- `PrimeRL/release/`
  - generated installer and packaged app outputs

## Current Source Mapping (Phase 1)
- existing code remains in `src/PrimeRLrl/` during transition
- current `tools/` and sequence files remain where they are until path resolver migration
- this folder is scaffolded now to support phased migration without breaking current workflow

## Migration Notes
1. Add centralized path resolver (`dev` vs `packaged`).
2. Move binary/database defaults to PrimeRL structure.
3. Update launcher and packaging to read from this structure.
4. Keep legacy fallback paths until installer is in place.
