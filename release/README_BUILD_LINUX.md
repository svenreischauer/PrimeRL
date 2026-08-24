# PrimeRL Linux Packaging

This guide covers Linux standalone packaging for PrimeRL.

## Target
- Architecture: `x86_64`
- Compiler policy for native tools: `clang` with `-march=x86-64-v3`
- Primary artifact: Debian package (`.deb`)

## Prerequisites
- Linux build host
- `python3`, `venv`, `pip`
- `clang`, `make`
- `dpkg-deb`
- `curl`

## 1) Prepare Tool Binaries
Build and stage native tools to `PrimeRL/tools/bin` (or `tools/bin` in flat layout):

```bash
./release/scripts/prepare_linux_tools.sh \
  --primer3-src ./third_party/sources/primer3 \
  --spidey-src ./third_party/sources/spidey \
  --spidey-cmd "make -j$(nproc)" \
  --spidey-bin spidey
```

Expected staged tools:
- `primer3_core`
- `ntthal`
- `oligotm`
- `spidey`
- `mfeprimer`
- `primer3_config/`

By default, MFEprimer is fetched from:
- `https://github.com/quwubin/MFEprimer-3.0/releases`

You can override with:

```bash
--mfe-url "https://github.com/quwubin/MFEprimer-3.0/releases"
```

For NCBI toolkit Spidey sources that do not build cleanly with modern clang,
use fallback mode (compile `spideymain.c` directly against NCBI shared libs):

```bash
micromamba run -p ~/.micromamba/envs/primerl-clang \
  ./release/scripts/prepare_linux_tools.sh \
    --primer3-src "/home/sven/projects/Primer3/HiDrive-Primer3 Source code package optimized 150226" \
    --spidey-src /tmp/ncbi-tools6-6.1.20170106+dfsg2 \
    --spidey-main demo/spideymain.c \
    --spidey-inc /tmp/ncbi-tools6-6.1.20170106+dfsg2/include \
    --spidey-lib /tmp/libncbi-extract-180517/usr/lib/x86_64-linux-gnu \
    --mfe-url https://github.com/quwubin/MFEprimer-3.0/releases \
    --clean
```

## 2) Build Linux App Bundle
No databases (default profile):

```bash
./release/scripts/build_linux_app.sh --version 1.3.3 --clean
```

With bundled databases:

```bash
./release/scripts/build_linux_app.sh --version 1.3.3 --clean --with-databases
```

Output (no DB):
- `release/PrimeRL_1.3.3_app_linux_x86_64_nodb/dist/PrimeRL`

## 3) Build Debian Package

```bash
./release/scripts/build_deb.sh --version 1.3.3 --clean \
  --app-dir release/PrimeRL_1.3.3_app_linux_x86_64_nodb/dist/PrimeRL
```

Output:
- `release/PrimeRL_1.3.3_deb_amd64/dist/primerl_1.3.3_amd64.deb`

## 4) Smoke Test
Install:

```bash
sudo dpkg -i release/PrimeRL_1.3.3_deb_amd64/dist/primerl_1.3.3_amd64.deb
```

Launch:

```bash
primerl
```

## Notes
- Runtime mutable data is written to `~/.primerl` when running frozen builds.
- You can override data location with `PRIMERL_DATA_DIR`.
- Installer does not fetch or compile dependencies.
