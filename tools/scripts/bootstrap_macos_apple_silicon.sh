#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

APP_ROOT="$REPO_ROOT"
if [[ -d "$REPO_ROOT/PrimeRL/runtime" && -d "$REPO_ROOT/PrimeRL/databases" ]]; then
  APP_ROOT="$REPO_ROOT/PrimeRL"
fi

echo "PrimeRL macOS Apple Silicon bootstrap"
echo "Repo: $REPO_ROOT"
echo "Runtime root: $APP_ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Warning: this script is intended for macOS (Darwin)."
fi
if [[ "$(uname -m)" != "arm64" ]]; then
  echo "Warning: this script targets Apple Silicon (arm64)."
fi

mkdir -p "$APP_ROOT/tools/bin"
mkdir -p "$APP_ROOT/tools/bin/clang_profiles/apple_silicon"
mkdir -p "$APP_ROOT/tools/bin/primer3_config"
mkdir -p "$APP_ROOT/databases/ensembl"
mkdir -p "$APP_ROOT/databases/refseq"
mkdir -p "$APP_ROOT/runtime/logs" "$APP_ROOT/runtime/tmp" "$APP_ROOT/runtime/cache" "$APP_ROOT/runtime/exports"

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

check_tool primer3_core "$APP_ROOT/tools/bin/primer3_core"
check_tool ntthal "$APP_ROOT/tools/bin/ntthal"
check_tool oligotm "$APP_ROOT/tools/bin/oligotm"
check_tool spidey "$APP_ROOT/tools/bin/spidey"
check_tool mfeprimer "$APP_ROOT/tools/bin/mfeprimer"

echo
echo "Next steps (manual/source-only):"
echo "  1) Build Primer3 binaries for arm64 and place under $APP_ROOT/tools/bin/ and/or clang_profiles/apple_silicon/."
echo "  2) Build Spidey for arm64 and place it under $APP_ROOT/tools/bin/spidey."
echo "  3) Download mfeprimer darwin_arm64 and place executable in $APP_ROOT/tools/bin/mfeprimer."
echo "  4) Copy/download required FASTA databases into $APP_ROOT/databases/."
