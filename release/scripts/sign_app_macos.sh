#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Sign a PrimeRL.app bundle on macOS.

Usage:
  ./release/scripts/sign_app_macos.sh [options]

Options:
  --app <path>          Path to PrimeRL.app (defaults to latest release build)
  --identity <id>       Signing identity (default: "-" for ad-hoc signing)
  --entitlements <file> Optional entitlements plist for top-level app signing
  -h, --help            Show this help
EOF
}

APP_PATH=""
SIGN_IDENTITY="-"
ENTITLEMENTS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app)
      APP_PATH="${2:-}"
      shift 2
      ;;
    --identity)
      SIGN_IDENTITY="${2:-}"
      shift 2
      ;;
    --entitlements)
      ENTITLEMENTS="${2:-}"
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

if [[ -z "$APP_PATH" ]]; then
  LATEST_APP=""
  while IFS= read -r -d '' candidate; do
    if [[ -z "$LATEST_APP" || "$candidate" -nt "$LATEST_APP" ]]; then
      LATEST_APP="$candidate"
    fi
  done < <(find "$REPO_ROOT/release" -maxdepth 4 -type d -path "*/dist/PrimeRL.app" -print0 2>/dev/null)
  APP_PATH="$LATEST_APP"
fi

if [[ -z "$APP_PATH" || ! -d "$APP_PATH" ]]; then
  echo "Error: app bundle not found. Use --app <path>." >&2
  exit 1
fi

if [[ -n "$ENTITLEMENTS" && ! -f "$ENTITLEMENTS" ]]; then
  echo "Error: entitlements file not found: $ENTITLEMENTS" >&2
  exit 1
fi

if ! command -v codesign >/dev/null 2>&1; then
  echo "Error: codesign tool not found." >&2
  exit 1
fi

SIGN_ARGS=(--force --sign "$SIGN_IDENTITY")
if [[ "$SIGN_IDENTITY" != "-" ]]; then
  SIGN_ARGS+=(--options runtime --timestamp)
fi

echo "Signing nested binaries in: $APP_PATH"
while IFS= read -r -d '' file; do
  codesign "${SIGN_ARGS[@]}" "$file"
done < <(
  find "$APP_PATH/Contents" -type f \
    \( -name "*.dylib" -o -name "*.so" -o -name "*.bundle" -o -perm -111 \) \
    -print0 | sort -z
)

echo "Signing app bundle: $APP_PATH"
TOP_SIGN_ARGS=("${SIGN_ARGS[@]}")
if [[ -n "$ENTITLEMENTS" ]]; then
  TOP_SIGN_ARGS+=(--entitlements "$ENTITLEMENTS")
fi
codesign "${TOP_SIGN_ARGS[@]}" "$APP_PATH"

echo "Verifying signature ..."
codesign --verify --deep --strict --verbose=2 "$APP_PATH"
codesign -dv --verbose=4 "$APP_PATH" 2>&1 | sed -n '1,20p'

if [[ "$SIGN_IDENTITY" != "-" ]]; then
  if command -v spctl >/dev/null 2>&1; then
    echo "Gatekeeper assessment:"
    spctl --assess --type execute --verbose "$APP_PATH"
  fi
else
  echo "Ad-hoc signing complete (identity '-')."
  echo "Use --identity \"Developer ID Application: ...\" for distributable signing."
fi
