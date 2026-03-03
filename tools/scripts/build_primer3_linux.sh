#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Build Primer3 Linux binaries with clang and x86-64-v3 baseline.

Usage:
  ./tools/scripts/build_primer3_linux.sh [options]

Options:
  --src-dir <dir>      Primer3 source root (default: third_party/sources/primer3)
  --out-dir <dir>      Output tool bin directory (default: PrimeRL/tools/bin or tools/bin)
  --clean              Run make clean before build
  --jobs <n>           Parallel jobs for make (default: nproc or 4)
  -h, --help           Show this help

Notes:
  - This script expects a Primer3 tree with a Makefile under <src-dir>/src.
  - Compiler policy is fixed to clang + -march=x86-64-v3.
EOF
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

SRC_DIR="$REPO_ROOT/third_party/sources/primer3"
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
OUT_DIR="$APP_ROOT/tools/bin"
CLEAN=0
JOBS="$(command -v nproc >/dev/null 2>&1 && nproc || echo 4)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --src-dir)
      SRC_DIR="${2:-}"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="${2:-}"
      shift 2
      ;;
    --clean)
      CLEAN=1
      shift
      ;;
    --jobs)
      JOBS="${2:-}"
      shift 2
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
  echo "Error: Linux is required for this build." >&2
  exit 1
fi

if ! command -v make >/dev/null 2>&1; then
  echo "Error: make is required." >&2
  exit 1
fi

pick_compiler() {
  local found=""
  for c in clang clang-21 clang-20 clang-19 clang-18 clang-17 clang-16 x86_64-conda-linux-gnu-clang; do
    if command -v "$c" >/dev/null 2>&1; then
      found="$c"
      break
    fi
  done
  if [[ -z "$found" ]]; then
    return 1
  fi
  printf '%s' "$found"
}

pick_cxx() {
  local found=""
  for c in clang++ clang++-21 clang++-20 clang++-19 clang++-18 clang++-17 clang++-16 x86_64-conda-linux-gnu-clang++; do
    if command -v "$c" >/dev/null 2>&1; then
      found="$c"
      break
    fi
  done
  if [[ -z "$found" ]]; then
    return 1
  fi
  printf '%s' "$found"
}

CC_BIN="$(pick_compiler || true)"
CXX_BIN="$(pick_cxx || true)"
if [[ -z "$CC_BIN" || -z "$CXX_BIN" ]]; then
  echo "Error: clang/clang++ are required." >&2
  exit 1
fi

if [[ ! -d "$SRC_DIR" ]]; then
  echo "Error: Primer3 source directory not found: $SRC_DIR" >&2
  exit 1
fi
SRC_DIR="$(cd -- "$SRC_DIR" && pwd)"
OUT_DIR="$(mkdir -p "$OUT_DIR" && cd -- "$OUT_DIR" && pwd)"
SRC_BUILD_DIR="$SRC_DIR/src"
SRC_LINK=""

cleanup() {
  if [[ -n "$SRC_LINK" && -L "$SRC_LINK" ]]; then
    rm -f "$SRC_LINK"
  fi
}
trap cleanup EXIT

if [[ ! -d "$SRC_BUILD_DIR" ]]; then
  echo "Error: expected Primer3 build directory at $SRC_BUILD_DIR" >&2
  echo "Hint: place Primer3 source at third_party/sources/primer3 or pass --src-dir." >&2
  exit 1
fi
if [[ ! -f "$SRC_BUILD_DIR/Makefile" ]]; then
  echo "Error: Primer3 Makefile not found in $SRC_BUILD_DIR" >&2
  exit 1
fi

# Some toolchains fail to emit relative '-o' artifacts from directories that
# contain whitespace. Use a temporary symlink with a safe path in that case.
if [[ "$SRC_DIR" == *" "* ]]; then
  SRC_LINK="/tmp/primer3_src_${RANDOM}_$$"
  ln -s "$SRC_DIR" "$SRC_LINK"
  SRC_DIR="$SRC_LINK"
  SRC_BUILD_DIR="$SRC_DIR/src"
fi

COMMON_FLAGS="-O3 -march=x86-64-v3 -mtune=generic -fomit-frame-pointer -DNDEBUG"

echo "Building Primer3 tools with clang"
echo "Source:  $SRC_BUILD_DIR"
echo "Output:  $OUT_DIR"
echo "Flags:   $COMMON_FLAGS"
echo "Jobs:    $JOBS"
echo "CC:      $CC_BIN"
echo "CXX:     $CXX_BIN"

pushd "$SRC_BUILD_DIR" >/dev/null

if [[ "$CLEAN" -eq 1 ]]; then
  # Some upstream snapshots have a broken recursive clean target when ../test
  # is absent; perform an in-tree cleanup explicitly instead.
  rm -f ./*.o ./*.a ./*.so ./*.so.* ./primer3_core ./ntthal ./oligotm ./amplicon3_core ./ntdpal ./primer3_masker ./long_seq_tm_test
fi

make -j"$JOBS" \
  CC="$CC_BIN" \
  CXX="$CXX_BIN" \
  CFLAGS="$COMMON_FLAGS" \
  CPPFLAGS="$COMMON_FLAGS"

for bin in primer3_core ntthal oligotm; do
  if [[ ! -x "$SRC_BUILD_DIR/$bin" ]]; then
    echo "Error: expected build output missing: $SRC_BUILD_DIR/$bin" >&2
    exit 1
  fi
  install -m 0755 "$SRC_BUILD_DIR/$bin" "$OUT_DIR/$bin"
done

if [[ -d "$SRC_BUILD_DIR/primer3_config" ]]; then
  rm -rf "$OUT_DIR/primer3_config"
  cp -a "$SRC_BUILD_DIR/primer3_config" "$OUT_DIR/primer3_config"
fi

popd >/dev/null

echo "Done. Installed:"
echo "  $OUT_DIR/primer3_core"
echo "  $OUT_DIR/ntthal"
echo "  $OUT_DIR/oligotm"
if [[ -d "$OUT_DIR/primer3_config" ]]; then
  echo "  $OUT_DIR/primer3_config/"
fi
