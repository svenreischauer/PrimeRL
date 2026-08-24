# Changelog

## 1.3.3 - 2026-08-24

### Fixed

- Use the native MSI feature-selection page for the optional desktop shortcut.

## 1.3.2 - 2026-08-24

### Fixed

- Corrected the WiX 6 installer definition for the desktop-shortcut choice.

## 1.3.1 - 2026-08-24

### Fixed

- Corrected the main window title to show PrimeRL v1.3.1.
- Added an explicit, default-on installer choice for creating a desktop shortcut.

## 1.3.0 - 2026-08-22

### Changed

- Updated MFEprimer to 4.5.1 and use the index-selected automatic `k` value.
- Removed the legacy `k` sensitivity presets while retaining non-`k` specificity controls.
- Switched MFEprimer databases to binary `.primerqc.bin` indexes; rebuild existing indexes from their transcriptome FASTA files.
- Updated bundled build dependencies and third-party tooling metadata.

### Fixed

- Handle MFEprimer 4.5.1 correctly when working paths are absolute Windows paths.
