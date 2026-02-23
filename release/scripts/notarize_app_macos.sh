#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Notarize a PrimeRL.app bundle on macOS and staple the ticket.

Usage:
  ./release/scripts/notarize_app_macos.sh [options]

Options:
  --app <path>               Path to PrimeRL.app (defaults to latest release build)
  --zip <path>               Output zip path (default: next to app)
  --sign-identity <id>       Re-sign app before notarization
  --keychain-profile <name>  notarytool keychain profile name (recommended)
  --apple-id <id>            Apple ID (fallback auth mode)
  --team-id <id>             Apple team ID (required with --apple-id)
  --password <value>         App-specific password or app store connect keychain item
  --skip-staple              Skip stapler step
  -h, --help                 Show this help
EOF
}

APP_PATH=""
ZIP_PATH=""
SIGN_IDENTITY=""
KEYCHAIN_PROFILE=""
APPLE_ID=""
TEAM_ID=""
PASSWORD=""
SKIP_STAPLE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app)
      APP_PATH="${2:-}"
      shift 2
      ;;
    --zip)
      ZIP_PATH="${2:-}"
      shift 2
      ;;
    --sign-identity)
      SIGN_IDENTITY="${2:-}"
      shift 2
      ;;
    --keychain-profile)
      KEYCHAIN_PROFILE="${2:-}"
      shift 2
      ;;
    --apple-id)
      APPLE_ID="${2:-}"
      shift 2
      ;;
    --team-id)
      TEAM_ID="${2:-}"
      shift 2
      ;;
    --password)
      PASSWORD="${2:-}"
      shift 2
      ;;
    --skip-staple)
      SKIP_STAPLE=1
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

if ! command -v xcrun >/dev/null 2>&1; then
  echo "Error: xcrun not found (install Xcode command line tools)." >&2
  exit 1
fi
if ! command -v ditto >/dev/null 2>&1; then
  echo "Error: ditto not found." >&2
  exit 1
fi

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

if [[ -n "$SIGN_IDENTITY" ]]; then
  "$REPO_ROOT/release/scripts/sign_app_macos.sh" --app "$APP_PATH" --identity "$SIGN_IDENTITY"
fi

if [[ -z "$KEYCHAIN_PROFILE" ]]; then
  if [[ -z "$APPLE_ID" || -z "$TEAM_ID" || -z "$PASSWORD" ]]; then
    echo "Error: provide either --keychain-profile or (--apple-id --team-id --password)." >&2
    exit 1
  fi
fi

if [[ -z "$ZIP_PATH" ]]; then
  APP_PARENT="$(cd -- "$(dirname -- "$APP_PATH")" && pwd)"
  APP_BASE="$(basename -- "$APP_PATH" .app)"
  ZIP_PATH="$APP_PARENT/${APP_BASE}_notary.zip"
fi

rm -f "$ZIP_PATH"
echo "Creating notarization archive: $ZIP_PATH"
ditto -c -k --keepParent "$APP_PATH" "$ZIP_PATH"

echo "Submitting to Apple notarization service ..."
NOTARY_OUT="$(mktemp)"
if [[ -n "$KEYCHAIN_PROFILE" ]]; then
  xcrun notarytool submit "$ZIP_PATH" \
    --keychain-profile "$KEYCHAIN_PROFILE" \
    --wait \
    --output-format json | tee "$NOTARY_OUT"
else
  xcrun notarytool submit "$ZIP_PATH" \
    --apple-id "$APPLE_ID" \
    --team-id "$TEAM_ID" \
    --password "$PASSWORD" \
    --wait \
    --output-format json | tee "$NOTARY_OUT"
fi

if command -v python3 >/dev/null 2>&1; then
  SUBMISSION_ID="$(python3 - <<'PY' "$NOTARY_OUT"
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
print(str(data.get("id") or ""))
PY
)"
  if [[ -n "$SUBMISSION_ID" ]]; then
    echo "Notary submission id: $SUBMISSION_ID"
  fi
fi
rm -f "$NOTARY_OUT"

if [[ "$SKIP_STAPLE" -eq 0 ]]; then
  echo "Stapling ticket to app ..."
  xcrun stapler staple "$APP_PATH"
  xcrun stapler validate "$APP_PATH"
fi

if command -v spctl >/dev/null 2>&1; then
  echo "Gatekeeper assessment:"
  spctl --assess --type execute --verbose "$APP_PATH"
fi

echo "Done."
