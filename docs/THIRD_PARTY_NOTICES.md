# Third-Party Notices

This document summarizes third-party components used by PrimeRL runtime and where their license texts/terms are stored in this repository.

## Components

| Component | Runtime Artifact / Usage | License / Terms | Local Notice Path |
|---|---|---|---|
| Primer3 | `primer3_core`, `ntthal`, `oligotm` | GPL-2.0 (Primer3), plus GPL-3.0 for Amplicon3 component | `third_party/licenses/primer3/LICENSE.GPL-2.0.txt`, `third_party/licenses/primer3/LICENSE_GPL3_for_Amplicon3.txt` |
| curl / libcurl | `PrimeRL/tools/bin/curl.exe` | curl license plus notices for statically linked libraries | `third_party/licenses/curl/` |
| OpenPyXL | Python Excel export dependency | MIT License | `third_party/licenses/openpyxl/LICENSE.MIT.txt` |
| MFEprimer | `PrimeRL/tools/bin/mfeprimer.exe` | Upstream use statement: command-line tools and online servers are free for nonprofit and commercial users | `third_party/licenses/mfeprimer/TERMS_NOTE.txt` |
| Splign / Spidey (NCBI) | `Splign.exe`, `Spidey.exe`, `Spidey_AVX2_FMA3.exe` | NCBI U.S. Government Work / public-domain notice | `third_party/licenses/spidey/NCBI_NOTICE.txt` |

## Source References

- Primer3 source and licenses in this repo: `third_party/primer3_src`
- curl license references: https://curl.se/docs/copyright.html , https://curl.se/docs/license.html
- OpenPyXL project/license reference: https://pypi.org/project/openpyxl/
- MFEprimer project page: https://www.mfeprimer.com/
- MFEprimer current use statement: https://www.mfeprimer.com/license/
- MFEprimer source/license reference: https://github.com/quwubin/MFEprimer-3.0
- MFEprimer historical terms reference: https://github.com/quwubin/MFEprimer-2.0
- NCBI legal/disclaimer notice (for NCBI software terms): https://www.ncbi.nlm.nih.gov/home/about/policies/#disclaimer
- NCBI public-domain notice text: https://ncbi.github.io/cxx-toolkit/pages/ch_public

## Packaging Note

When distributing builds publicly, include this file and the full texts in `third_party/licenses/`.
If a binary is replaced with a different upstream version, update this notices file and the corresponding license/terms files.
