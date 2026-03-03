#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Prepare Linux runtime binaries for PrimeRL release packaging.

This script stages required tool binaries into PrimeRL/tools/bin:
  - primer3_core
  - ntthal
  - oligotm
  - spidey
  - mfeprimer
  - primer3_config/

Usage:
  ./release/scripts/prepare_linux_tools.sh [options]

Options:
  --primer3-src <dir>  Primer3 source root for build_primer3_linux.sh
  --spidey-src <dir>   Spidey source directory for build_spidey_linux.sh
  --spidey-cmd <cmd>   Optional custom build command for Spidey
  --spidey-bin <path>  Relative built spidey binary path in --spidey-src
  --spidey-main <path> Relative spidey main C file for fallback compile mode
  --spidey-inc <dir>   Include directory for Spidey fallback compile mode
  --spidey-lib <dir>   NCBI shared-library directory for Spidey fallback mode
  --mfe-url <url>      MFEprimer download URL (default: latest GitHub release page)
  --mfe-sha256 <sum>   Optional checksum for MFEprimer download
  --skip-primer3       Do not build Primer3/ntthal/oligotm
  --skip-spidey        Do not build Spidey
  --skip-mfeprimer     Do not fetch MFEprimer
  --clean              Remove existing staged binaries before processing
  -h, --help           Show this help
EOF
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
TOOLS_SCRIPT_DIR="$REPO_ROOT/tools/scripts"

APP_ROOT="$REPO_ROOT"
if [[ -d "$REPO_ROOT/PrimeRL/runtime" && -d "$REPO_ROOT/PrimeRL/tools" ]]; then
  score_asset_root() {
    local root="$1"
    local score=0
    if [[ -d "$root/runtime" ]]; then
      score=$((score + 1))
    fi
    if [[ -d "$root/tools" ]]; then
      score=$((score + 1))
    fi
    for bin in primer3_core ntthal spidey mfeprimer; do
      if [[ -x "$root/tools/bin/$bin" ]]; then
        score=$((score + 10))
      fi
    done
    printf '%s' "$score"
  }
  root_score="$(score_asset_root "$REPO_ROOT")"
  nested_score="$(score_asset_root "$REPO_ROOT/PrimeRL")"
  if [[ "$nested_score" -gt "$root_score" ]]; then
    APP_ROOT="$REPO_ROOT/PrimeRL"
  fi
fi
TOOLS_BIN="$APP_ROOT/tools/bin"

PRIMER3_SRC="$REPO_ROOT/third_party/sources/primer3"
SPIDEY_SRC="$REPO_ROOT/third_party/sources/spidey"
SPIDEY_CMD=""
SPIDEY_BIN="spidey"
SPIDEY_MAIN=""
SPIDEY_INC=""
SPIDEY_LIB=""
MFE_URL="https://github.com/quwubin/MFEprimer-3.0/releases"
MFE_SHA256=""
SKIP_PRIMER3=0
SKIP_SPIDEY=0
SKIP_MFE=0
CLEAN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --primer3-src)
      PRIMER3_SRC="${2:-}"
      shift 2
      ;;
    --spidey-src)
      SPIDEY_SRC="${2:-}"
      shift 2
      ;;
    --spidey-cmd)
      SPIDEY_CMD="${2:-}"
      shift 2
      ;;
    --spidey-bin)
      SPIDEY_BIN="${2:-}"
      shift 2
      ;;
    --spidey-main)
      SPIDEY_MAIN="${2:-}"
      shift 2
      ;;
    --spidey-inc)
      SPIDEY_INC="${2:-}"
      shift 2
      ;;
    --spidey-lib)
      SPIDEY_LIB="${2:-}"
      shift 2
      ;;
    --mfe-url)
      MFE_URL="${2:-}"
      shift 2
      ;;
    --mfe-sha256)
      MFE_SHA256="${2:-}"
      shift 2
      ;;
    --skip-primer3)
      SKIP_PRIMER3=1
      shift
      ;;
    --skip-spidey)
      SKIP_SPIDEY=1
      shift
      ;;
    --skip-mfeprimer)
      SKIP_MFE=1
      shift
      ;;
    --clean)
      CLEAN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Error: Linux is required for tool preparation." >&2
  exit 1
fi

mkdir -p "$TOOLS_BIN"

if [[ "$CLEAN" -eq 1 ]]; then
  rm -f "$TOOLS_BIN/primer3_core" "$TOOLS_BIN/ntthal" "$TOOLS_BIN/oligotm" "$TOOLS_BIN/spidey" "$TOOLS_BIN/mfeprimer"
  rm -rf "$TOOLS_BIN/primer3_config"
fi

if [[ "$SKIP_PRIMER3" -eq 0 ]]; then
  "$TOOLS_SCRIPT_DIR/build_primer3_linux.sh" --src-dir "$PRIMER3_SRC" --out-dir "$TOOLS_BIN"
fi

if [[ "$SKIP_SPIDEY" -eq 0 ]]; then
  SPIDEY_ARGS=(--src-dir "$SPIDEY_SRC" --out-dir "$TOOLS_BIN" --binary-path "$SPIDEY_BIN")
  if [[ -n "$SPIDEY_CMD" ]]; then
    SPIDEY_ARGS+=(--build-cmd "$SPIDEY_CMD")
  fi
  if [[ -n "$SPIDEY_MAIN" ]]; then
    SPIDEY_ARGS+=(--spidey-main "$SPIDEY_MAIN")
  fi
  if [[ -n "$SPIDEY_INC" ]]; then
    SPIDEY_ARGS+=(--include-dir "$SPIDEY_INC")
  fi
  if [[ -n "$SPIDEY_LIB" ]]; then
    SPIDEY_ARGS+=(--ncbi-lib-dir "$SPIDEY_LIB")
  fi
  "$TOOLS_SCRIPT_DIR/build_spidey_linux.sh" "${SPIDEY_ARGS[@]}"
fi

if [[ "$SKIP_MFE" -eq 0 ]]; then
  MFE_ARGS=(--url "$MFE_URL" --out-dir "$TOOLS_BIN")
  if [[ -n "$MFE_SHA256" ]]; then
    MFE_ARGS+=(--sha256 "$MFE_SHA256")
  fi
  "$TOOLS_SCRIPT_DIR/fetch_mfeprimer_linux.sh" "${MFE_ARGS[@]}"
fi

missing=0
for req in primer3_core ntthal spidey; do
  if [[ ! -x "$TOOLS_BIN/$req" ]]; then
    echo "Missing required binary: $TOOLS_BIN/$req" >&2
    missing=1
  fi
done
if [[ ! -d "$TOOLS_BIN/primer3_config" ]]; then
  echo "Warning: primer3_config was not staged under $TOOLS_BIN/primer3_config" >&2
fi
if [[ ! -x "$TOOLS_BIN/mfeprimer" ]]; then
  echo "Warning: mfeprimer not found at $TOOLS_BIN/mfeprimer (MFE-based features will be limited)." >&2
fi

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

echo "Linux tools prepared successfully in $TOOLS_BIN"
