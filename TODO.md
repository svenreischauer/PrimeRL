# TODO

- [ ] Create baseline commit for `02_DeepPrime_Workspace` (known-good starting snapshot).
- [ ] Execute native Splign replacement plan in `docs/PLAN_SPLIGN_NATIVE_BUILD.md`.
- [ ] Reorder filtering pipeline.
- [ ] Fix excessive SNP data handling for human samples.

## Low Complexity Filter Plan

- [ ] Define filter scope and defaults:
  - [ ] Add optional `Low complexity filter` toggle (default `on`).
  - [ ] Add `Strictness` selector (`lenient`, `balanced`, `strict`).
- [ ] Implement phase 1 (pure Python prefilter, no new binaries):
  - [ ] Shannon entropy check on primer sequences (mono + di-nucleotide).
  - [ ] Periodicity/motif check (short tandem motif overrepresentation).
  - [ ] Keep existing homopolymer/run checks as independent signals.
- [ ] Insert filter in pipeline before expensive checks:
  - [ ] Run low-complexity filter before ntthal cutoff / MFE dimer / transcriptome specificity.
  - [ ] Ensure filtered pair count is reflected in status and final summary.
- [ ] Observability and UX:
  - [ ] Add per-run counters (`removed_low_complexity`, reason breakdown).
  - [ ] Include low-complexity stage messages in status popup.
  - [ ] Include low-complexity removal slice in filter pie chart.
- [ ] Validation:
  - [ ] Add unit tests for entropy/motif edge cases and threshold boundaries.
  - [ ] Add regression test to ensure strictness levels reduce candidates monotonically.
  - [ ] Run full test suite and smoke-test GUI with/without filter enabled.
- [ ] Optional phase 2:
  - [ ] Evaluate DUST-like scoring for closer BLAST-style low-complexity behavior.
  - [ ] Compare phase 1 vs DUST on representative genes for false-positive/false-negative tradeoff.
