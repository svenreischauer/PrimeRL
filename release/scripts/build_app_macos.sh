#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Build PrimeRL.app on macOS (Apple Silicon) with PyInstaller.

Usage:
  ./release/scripts/build_app_macos.sh [options]

Options:
  --version <ver>       Version tag used in output folder name (default: 1.1)
  --clean               Remove previous output folder before build
  --with-databases      Include bundled databases in the app payload
  --sign                Sign app after build (ad-hoc by default)
  --sign-identity <id>  Signing identity, e.g. "Developer ID Application: Your Name (TEAMID)"
  -h, --help            Show this help
EOF
}

VERSION="1.1"
CLEAN=0
WITH_DATABASES=0
SIGN_AFTER_BUILD=0
SIGN_IDENTITY=""

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
    --sign)
      SIGN_AFTER_BUILD=1
      shift
      ;;
    --sign-identity)
      SIGN_AFTER_BUILD=1
      SIGN_IDENTITY="${2:-}"
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

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Error: macOS is required to build a .app bundle." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 not found." >&2
  exit 1
fi

ASSET_ROOT="$REPO_ROOT"
if [[ -d "$REPO_ROOT/PrimeRL/runtime" && -d "$REPO_ROOT/PrimeRL/tools" ]]; then
  ASSET_ROOT="$REPO_ROOT/PrimeRL"
fi

OUTPUT_ROOT="$REPO_ROOT/release/PrimeRL_${VERSION}_app_macos_arm64_nodb"
if [[ "$WITH_DATABASES" -eq 1 ]]; then
  OUTPUT_ROOT="$REPO_ROOT/release/PrimeRL_${VERSION}_app_macos_arm64"
fi
WORK_ROOT="$OUTPUT_ROOT/build"
DIST_ROOT="$OUTPUT_ROOT/dist"
SPEC_ROOT="$OUTPUT_ROOT"

if [[ "$CLEAN" -eq 1 && -d "$OUTPUT_ROOT" ]]; then
  rm -rf "$OUTPUT_ROOT"
fi
mkdir -p "$WORK_ROOT" "$DIST_ROOT" "$SPEC_ROOT"

if [[ ! -d "$REPO_ROOT/.venv" ]]; then
  python3 -m venv --system-site-packages "$REPO_ROOT/.venv"
fi
PYTHON_BIN="$REPO_ROOT/.venv/bin/python"

"$PYTHON_BIN" -m pip install --quiet --disable-pip-version-check pyinstaller ttkbootstrap openpyxl

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

echo "Building PrimeRL.app ..."
echo "Repo root: $REPO_ROOT"
echo "Asset root: $ASSET_ROOT"
echo "Output: $OUTPUT_ROOT"

"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name PrimeRL \
  --paths "$REPO_ROOT/src" \
  --hidden-import primerl.gui \
  --collect-data ttkbootstrap \
  --workpath "$WORK_ROOT" \
  --distpath "$DIST_ROOT" \
  --specpath "$SPEC_ROOT" \
  "${ADD_DATA_ARGS[@]}" \
  "$REPO_ROOT/run_gui.py"

APP_PATH="$DIST_ROOT/PrimeRL.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "Build finished but app bundle not found: $APP_PATH" >&2
  exit 1
fi

echo "Built app: $APP_PATH"

if [[ "$SIGN_AFTER_BUILD" -eq 1 ]]; then
  SIGN_SCRIPT="$REPO_ROOT/release/scripts/sign_app_macos.sh"
  if [[ -n "$SIGN_IDENTITY" ]]; then
    "$SIGN_SCRIPT" --app "$APP_PATH" --identity "$SIGN_IDENTITY"
  else
    "$SIGN_SCRIPT" --app "$APP_PATH"
  fi
fi
