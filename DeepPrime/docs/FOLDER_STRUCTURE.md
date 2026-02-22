# DeepPrime Folder Structure

## Proposed Runtime/Distribution Structure
- `DeepPrime/app/src/deepprime/`
  - future Python package root for GUI and app modules
- `DeepPrime/tools/bin/`
  - external binaries: `primer3_core`, `ntthal`, `oligotm`, `Spidey`, `mfeprimer`
- `DeepPrime/tools/scripts/`
  - maintenance/indexing scripts
- `DeepPrime/databases/ensembl/`
  - Ensembl FASTA + `.primerqc` index files
- `DeepPrime/databases/refseq/`
  - RefSeq FASTA + `.primerqc` index files
- `DeepPrime/config/`
  - default app settings, path presets
- `DeepPrime/runtime/logs/`
  - app logs
- `DeepPrime/runtime/tmp/`
  - temporary files
- `DeepPrime/runtime/cache/`
  - cached API/analysis artifacts
- `DeepPrime/release/`
  - generated installer and packaged app outputs

## Current Source Mapping (Phase 1)
- existing code remains in `src/deepprimerl/` during transition
- current `tools/` and sequence files remain where they are until path resolver migration
- this folder is scaffolded now to support phased migration without breaking current workflow

## Migration Notes
1. Add centralized path resolver (`dev` vs `packaged`).
2. Move binary/database defaults to DeepPrime structure.
3. Update launcher and packaging to read from this structure.
4. Keep legacy fallback paths until installer is in place.
