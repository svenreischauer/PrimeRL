#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

echo "PrimeRL macOS Apple Silicon bootstrap"
echo "Repo: $REPO_ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Warning: this script is intended for macOS (Darwin)."
fi
if [[ "$(uname -m)" != "arm64" ]]; then
  echo "Warning: this script targets Apple Silicon (arm64)."
fi

mkdir -p PrimeRL/tools/bin
mkdir -p PrimeRL/tools/bin/clang_profiles/apple_silicon
mkdir -p PrimeRL/tools/bin/primer3_config
mkdir -p PrimeRL/databases/ensembl
mkdir -p PrimeRL/databases/refseq
mkdir -p PrimeRL/runtime/logs PrimeRL/runtime/tmp PrimeRL/runtime/cache PrimeRL/runtime/exports
mkdir -p tools/bin databases runtime/logs runtime/tmp runtime/cache runtime/exports

echo
echo "Directory scaffolding created."

echo
echo "Tool checks:"
check_tool() {
  local name="$1"
  shift
  local found=0
  for p in "$@"; do
    if [[ -x "$p" ]]; then
      echo "  [ok] $name: $p"
      found=1
      break
    fi
  done
  if [[ "$found" -eq 0 ]]; then
    if command -v "$name" >/dev/null 2>&1; then
      echo "  [ok] $name: $(command -v "$name")"
      found=1
    fi
  fi
  if [[ "$found" -eq 0 ]]; then
    echo "  [missing] $name"
  fi
}

check_tool primer3_core PrimeRL/tools/bin/primer3_core tools/bin/primer3_core
check_tool ntthal PrimeRL/tools/bin/ntthal tools/bin/ntthal
check_tool oligotm PrimeRL/tools/bin/oligotm tools/bin/oligotm
check_tool spidey PrimeRL/tools/bin/spidey tools/bin/spidey
check_tool mfeprimer PrimeRL/tools/bin/mfeprimer tools/bin/mfeprimer
check_tool minimap2

echo
echo "Next steps (manual/source-only):"
echo "  1) Build Primer3 binaries for arm64 and place under PrimeRL/tools/bin/ and/or clang_profiles/apple_silicon/."
echo "  2) Build Spidey for arm64 or install minimap2 (brew install minimap2) as fallback."
echo "  3) Download mfeprimer darwin_arm64 and place executable in PrimeRL/tools/bin/mfeprimer."
echo "  4) Copy/download required FASTA databases into PrimeRL/databases/."
