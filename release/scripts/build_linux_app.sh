#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Build PrimeRL Linux app bundle with PyInstaller.

Usage:
  ./release/scripts/build_linux_app.sh [options]

Options:
  --version <ver>       Version tag used in output folder name (default: 1.3.1)
  --clean               Remove previous output folder before build
  --with-databases      Include bundled databases in app payload
  -h, --help            Show this help
EOF
}

VERSION="1.3.1"
CLEAN=0
WITH_DATABASES=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="${2:-}"
      shift 2
      ;;
    --clean)
      CLEAN=1
      shift
      ;;
    --with-databases)
      WITH_DATABASES=1
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

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Error: Linux is required to build the Linux app bundle." >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 not found." >&2
  exit 1
fi

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

ASSET_ROOT="$REPO_ROOT"
if [[ -d "$REPO_ROOT/PrimeRL/runtime" && -d "$REPO_ROOT/PrimeRL/tools" ]]; then
  root_score="$(score_asset_root "$REPO_ROOT")"
  nested_score="$(score_asset_root "$REPO_ROOT/PrimeRL")"
  if [[ "$nested_score" -gt "$root_score" ]]; then
    ASSET_ROOT="$REPO_ROOT/PrimeRL"
  fi
fi

OUTPUT_ROOT="$REPO_ROOT/release/PrimeRL_${VERSION}_app_linux_x86_64_nodb"
if [[ "$WITH_DATABASES" -eq 1 ]]; then
  OUTPUT_ROOT="$REPO_ROOT/release/PrimeRL_${VERSION}_app_linux_x86_64"
fi
WORK_ROOT="$OUTPUT_ROOT/build"
DIST_ROOT="$OUTPUT_ROOT/dist"
SPEC_ROOT="$OUTPUT_ROOT"

if [[ "$CLEAN" -eq 1 && -d "$OUTPUT_ROOT" ]]; then
  rm -rf "$OUTPUT_ROOT"
fi
mkdir -p "$WORK_ROOT" "$DIST_ROOT" "$SPEC_ROOT"

PYTHON_BIN=""
PIP_SCOPE_ARGS=()
if [[ -d "$REPO_ROOT/.venv" ]]; then
  cand="$REPO_ROOT/.venv/bin/python"
  if "$cand" -m pip --version >/dev/null 2>&1; then
    PYTHON_BIN="$cand"
  fi
else
  if python3 -m venv --system-site-packages "$REPO_ROOT/.venv" >/dev/null 2>&1; then
    cand="$REPO_ROOT/.venv/bin/python"
    if "$cand" -m pip --version >/dev/null 2>&1; then
      PYTHON_BIN="$cand"
    fi
  fi
fi

if [[ -z "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3)"
  PIP_SCOPE_ARGS=(--user)
else
  if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
    PIP_SCOPE_ARGS=(--user)
  else
    PIP_SCOPE_ARGS=()
  fi
fi

if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
  if command -v micromamba >/dev/null 2>&1; then
    MM_ENV="$HOME/.micromamba/envs/primerl-build-py"
    if [[ ! -x "$MM_ENV/bin/python" ]]; then
      micromamba create -y -p "$MM_ENV" python=3.12 pip >/dev/null
    fi
    PYTHON_BIN="$MM_ENV/bin/python"
    PIP_SCOPE_ARGS=()
  else
    echo "Error: no usable python+pip environment found (python3-venv/pip missing)." >&2
    exit 1
  fi
fi

"$PYTHON_BIN" -m pip install --quiet --disable-pip-version-check "${PIP_SCOPE_ARGS[@]}" \
  "pyinstaller>=6.22.2,<7" \
  "ttkbootstrap>=1.20.4,<2" \
  "openpyxl>=3.1.5,<4"

ADD_DATA_ARGS=()
add_data_dir() {
  local src="$1"
  local dst="$2"
  if [[ -d "$src" ]]; then
    ADD_DATA_ARGS+=(--add-data "$src:$dst")
  fi
}

add_data_dir "$ASSET_ROOT/config" "PrimeRL/config"
add_data_dir "$ASSET_ROOT/docs" "PrimeRL/docs"
add_data_dir "$ASSET_ROOT/runtime" "PrimeRL/runtime"
add_data_dir "$ASSET_ROOT/tools" "PrimeRL/tools"
if [[ "$WITH_DATABASES" -eq 1 ]]; then
  add_data_dir "$ASSET_ROOT/databases" "PrimeRL/databases"
fi
add_data_dir "$REPO_ROOT/third_party" "third_party"

echo "Building PrimeRL Linux bundle ..."
echo "Repo root:  $REPO_ROOT"
echo "Asset root: $ASSET_ROOT"
echo "Output:     $OUTPUT_ROOT"

"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name PrimeRL \
  --paths "$REPO_ROOT/src" \
  --hidden-import primerl.gui \
  --hidden-import PIL._tkinter_finder \
  --collect-data ttkbootstrap \
  --workpath "$WORK_ROOT" \
  --distpath "$DIST_ROOT" \
  --specpath "$SPEC_ROOT" \
  "${ADD_DATA_ARGS[@]}" \
  "$REPO_ROOT/run_gui.py"

APP_PATH="$DIST_ROOT/PrimeRL/PrimeRL"
if [[ ! -x "$APP_PATH" ]]; then
  echo "Build finished but executable not found: $APP_PATH" >&2
  exit 1
fi

echo "Built app bundle: $DIST_ROOT/PrimeRL"
