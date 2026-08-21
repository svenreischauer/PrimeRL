# Linux Release Policy

## Scope
This document defines how PrimeRL Linux standalone releases are produced.

## Distribution Model
- Git repository remains source-only.
- Linux tool binaries and release artifacts are built locally/CI and published as release assets.
- Runtime/databases are not committed to source control.

## Binary Provisioning Policy
- Build-time: allowed to compile/fetch third-party binaries.
- Installer-time: must not compile source and must not fetch dependencies.
- End-user installation must be deterministic and offline-capable once artifact is downloaded.

## Compiler Baseline
- Native binaries built from source must use:
  - `clang`
  - `-O3 -march=x86-64-v3 -mtune=generic -fomit-frame-pointer -DNDEBUG`

## Required Runtime Tools
- `primer3_core`
- `ntthal`
- `spidey`
- `mfeprimer` (unless disabled by policy/licensing decision)
- `primer3_config/`

## Optional Data
- Transcriptome FASTA and binary MFEprimer `.primerqc.bin` indexes may be shipped in optional/full profiles.
- Default Linux artifact should remain no-database (`nodb`) for manageable package size.

## Compliance
- Keep `docs/THIRD_PARTY_NOTICES.md` and `third_party/licenses/*` in sync with shipped binaries.
- Record source URL and checksums in `release/linux/tool_manifest.json`.
