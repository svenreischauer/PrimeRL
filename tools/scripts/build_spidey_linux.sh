#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Build Spidey Linux binary with clang and x86-64-v3 baseline.

Usage:
  ./tools/scripts/build_spidey_linux.sh [options]

Options:
  --src-dir <dir>      Spidey source directory (required)
  --out-dir <dir>      Output tool bin directory (default: PrimeRL/tools/bin or tools/bin)
  --build-cmd <cmd>    Optional custom build command (runs in --src-dir)
  --binary-path <path> Relative path to built spidey binary (default: spidey)
  --spidey-main <path> Relative path to spidey main C file (fallback mode)
  --include-dir <dir>  Include directory for fallback compile (default: <src-dir>/include)
  --ncbi-lib-dir <dir> Directory containing libncbi*.so shared libs for fallback compile
  --clean              Remove previous output binary before install
  -h, --help           Show this help

Notes:
  - Compiler policy is fixed to clang + -march=x86-64-v3.
  - Because Spidey is sourced from varying upstream trees, this script supports
    a custom --build-cmd, a best-effort Makefile flow, or direct compilation
    of NCBI `spideymain.c` against provided shared libraries.
EOF
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
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

SRC_DIR=""
OUT_DIR="$APP_ROOT/tools/bin"
BUILD_CMD=""
BINARY_REL="spidey"
SPIDEY_MAIN=""
INCLUDE_DIR=""
NCBI_LIB_DIR=""
CLEAN=0

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
    --build-cmd)
      BUILD_CMD="${2:-}"
      shift 2
      ;;
    --binary-path)
      BINARY_REL="${2:-}"
      shift 2
      ;;
    --spidey-main)
      SPIDEY_MAIN="${2:-}"
      shift 2
      ;;
    --include-dir)
      INCLUDE_DIR="${2:-}"
      shift 2
      ;;
    --ncbi-lib-dir)
      NCBI_LIB_DIR="${2:-}"
      shift 2
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
  echo "Error: Linux is required for this build." >&2
  exit 1
fi
if [[ -z "$SRC_DIR" ]]; then
  echo "Error: --src-dir is required." >&2
  exit 2
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

SRC_DIR="$(cd -- "$SRC_DIR" && pwd)"
OUT_DIR="$(mkdir -p "$OUT_DIR" && cd -- "$OUT_DIR" && pwd)"

if [[ ! -d "$SRC_DIR" ]]; then
  echo "Error: source directory not found: $SRC_DIR" >&2
  exit 1
fi

COMMON_FLAGS="-O3 -march=x86-64-v3 -mtune=generic -fomit-frame-pointer -DNDEBUG"

pick_shared_lib() {
  local dir="$1"
  local base="$2"
  local cand=""
  cand="$(find "$dir" -maxdepth 1 -type f -name "${base}.so*" | sort | head -n 1 || true)"
  if [[ -z "$cand" ]]; then
    return 1
  fi
  printf '%s' "$cand"
}

if [[ -n "$BUILD_CMD" ]]; then
  echo "Running custom Spidey build command in $SRC_DIR"
  (
    cd "$SRC_DIR"
    CC="$CC_BIN" CXX="$CXX_BIN" CFLAGS="$COMMON_FLAGS" CPPFLAGS="$COMMON_FLAGS" bash -lc "$BUILD_CMD"
  )
elif [[ -n "$SPIDEY_MAIN" || -f "$SRC_DIR/demo/spideymain.c" ]]; then
  if [[ -z "$SPIDEY_MAIN" ]]; then
    SPIDEY_MAIN="demo/spideymain.c"
  fi
  MAIN_PATH="$SPIDEY_MAIN"
  if [[ ! "$MAIN_PATH" = /* ]]; then
    MAIN_PATH="$SRC_DIR/$SPIDEY_MAIN"
  fi
  if [[ ! -f "$MAIN_PATH" ]]; then
    echo "Error: fallback main source not found: $MAIN_PATH" >&2
    exit 1
  fi

  if [[ -z "$INCLUDE_DIR" ]]; then
    INCLUDE_DIR="$SRC_DIR/include"
  fi
  if [[ ! "$INCLUDE_DIR" = /* ]]; then
    INCLUDE_DIR="$SRC_DIR/$INCLUDE_DIR"
  fi
  if [[ ! -d "$INCLUDE_DIR" ]]; then
    echo "Error: include directory not found for fallback compile: $INCLUDE_DIR" >&2
    echo "Hint: pass --include-dir (for example, from an NCBI toolkit build/include tree)." >&2
    exit 1
  fi

  if [[ -z "$NCBI_LIB_DIR" ]]; then
    if [[ -d "$OUT_DIR/lib" ]]; then
      NCBI_LIB_DIR="$OUT_DIR/lib"
    elif [[ -d "$APP_ROOT/tools/bin/lib" ]]; then
      NCBI_LIB_DIR="$APP_ROOT/tools/bin/lib"
    fi
  fi
  if [[ -z "$NCBI_LIB_DIR" ]]; then
    echo "Error: --ncbi-lib-dir is required for fallback Spidey compile." >&2
    exit 1
  fi
  if [[ ! "$NCBI_LIB_DIR" = /* ]]; then
    NCBI_LIB_DIR="$SRC_DIR/$NCBI_LIB_DIR"
  fi
  if [[ ! -d "$NCBI_LIB_DIR" ]]; then
    echo "Error: NCBI library directory not found: $NCBI_LIB_DIR" >&2
    exit 1
  fi

  libs=()
  for lib in libncbiid1 libncbitool libblastcompadj libnetcli libncbiobj libncbi; do
    lib_path="$(pick_shared_lib "$NCBI_LIB_DIR" "$lib" || true)"
    if [[ -z "$lib_path" ]]; then
      echo "Error: required shared library missing in $NCBI_LIB_DIR: ${lib}.so*" >&2
      exit 1
    fi
    libs+=("$lib_path")
  done

  BIN_PATH="$SRC_DIR/$BINARY_REL"
  mkdir -p "$(dirname "$BIN_PATH")"
  echo "Compiling Spidey fallback source with clang"
  echo "Main:    $MAIN_PATH"
  echo "Include: $INCLUDE_DIR"
  echo "Lib dir: $NCBI_LIB_DIR"
  "$CC_BIN" $COMMON_FLAGS -std=gnu89 -Wno-parentheses -I"$INCLUDE_DIR" "$MAIN_PATH" -o "$BIN_PATH" "${libs[@]}" -lm
else
  if [[ ! -f "$SRC_DIR/Makefile" ]]; then
    echo "Error: no Makefile found in $SRC_DIR and no compatible fallback source detected." >&2
    echo "Hint: provide --build-cmd or pass --spidey-main/--include-dir/--ncbi-lib-dir." >&2
    exit 1
  fi
  echo "Running default Spidey build via make"
  (
    cd "$SRC_DIR"
    make CC="$CC_BIN" CXX="$CXX_BIN" CFLAGS="$COMMON_FLAGS" CPPFLAGS="$COMMON_FLAGS"
  )
fi

BIN_PATH="$SRC_DIR/$BINARY_REL"
if [[ ! -x "$BIN_PATH" ]]; then
  echo "Error: built Spidey binary not found or not executable: $BIN_PATH" >&2
  echo "Hint: pass --binary-path with the correct relative path under --src-dir." >&2
  exit 1
fi

if [[ "$CLEAN" -eq 1 ]]; then
  rm -f "$OUT_DIR/spidey"
fi
install -m 0755 "$BIN_PATH" "$OUT_DIR/spidey"

echo "Done. Installed: $OUT_DIR/spidey"
