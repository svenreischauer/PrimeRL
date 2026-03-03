#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Fetch Linux MFEprimer binary and install it into PrimeRL tools/bin.

Usage:
  ./tools/scripts/fetch_mfeprimer_linux.sh [options]

Options:
  --url <url>          Download URL for mfeprimer Linux artifact (required)
  --sha256 <sum>       Optional sha256 checksum to verify
  --out-dir <dir>      Output tool bin directory (default: PrimeRL/tools/bin or tools/bin)
  --clean              Remove previously installed mfeprimer before install
  -h, --help           Show this help

Notes:
  - Supports direct executable download, .tar.gz/.tgz, .gz, or .zip archives.
  - You can pass a GitHub releases page URL; this script will resolve
    the latest Linux amd64 asset automatically.
  - The installed output file name is always: mfeprimer
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

URL=""
SHA256=""
OUT_DIR="$APP_ROOT/tools/bin"
CLEAN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      URL="${2:-}"
      shift 2
      ;;
    --sha256)
      SHA256="${2:-}"
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

if [[ -z "$URL" ]]; then
  echo "Error: --url is required." >&2
  exit 2
fi
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Error: Linux is required for this fetch script." >&2
  exit 1
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is required." >&2
  exit 1
fi
if ! command -v sha256sum >/dev/null 2>&1; then
  echo "Error: sha256sum is required." >&2
  exit 1
fi

resolve_github_release_asset() {
  local page_url="$1"
  python3 - "$page_url" <<'PY'
import json
import re
import sys
import urllib.parse
import urllib.request

url = sys.argv[1].strip()
rx = re.compile(
    r'^https?://github\.com/([^/]+)/([^/]+)/releases(?:/(latest|tag/[^/?#]+))?/?(?:[?#].*)?$'
)
m = rx.match(url)
if not m:
    print("")
    print("")
    sys.exit(0)

owner, repo, variant = m.group(1), m.group(2), m.group(3)
if variant and variant.startswith("tag/"):
    tag = variant.split("/", 1)[1]
    api = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{urllib.parse.quote(tag)}"
else:
    api = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"

req = urllib.request.Request(
    api,
    headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "primerl-fetch-mfeprimer"
    },
)
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.load(resp)

assets = data.get("assets") or []
if not assets:
    print("")
    print("")
    sys.exit(0)

def score(asset):
    name = (asset.get("name") or "").lower()
    s = 0
    if "linux" in name:
        s += 20
    if "amd64" in name or "x86_64" in name:
        s += 10
    if name.endswith(".gz") or name.endswith(".tgz") or name.endswith(".tar.gz"):
        s += 3
    if "mfeprimer" in name:
        s += 2
    return s

best = sorted(assets, key=score, reverse=True)[0]
download = best.get("browser_download_url") or ""
digest = best.get("digest") or ""
sha = ""
if digest.startswith("sha256:"):
    sha = digest.split(":", 1)[1]

print(download)
print(sha)
PY
}

if [[ "$URL" =~ ^https?://github\.com/[^/]+/[^/]+/releases(/.*)?/?$ ]] && \
   [[ "$URL" != *.tar.gz && "$URL" != *.tgz && "$URL" != *.zip && "$URL" != *.gz ]]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required to resolve GitHub release page URLs." >&2
    exit 1
  fi
  mapfile -t resolved < <(resolve_github_release_asset "$URL")
  if [[ -z "${resolved[0]:-}" ]]; then
    echo "Error: failed to resolve Linux MFEprimer asset from release URL: $URL" >&2
    exit 1
  fi
  echo "Resolved GitHub release URL:"
  echo "  Page:  $URL"
  URL="${resolved[0]}"
  echo "  Asset: $URL"
  if [[ -z "$SHA256" && -n "${resolved[1]:-}" ]]; then
    SHA256="${resolved[1]}"
    echo "  SHA256: $SHA256"
  fi
fi

OUT_DIR="$(mkdir -p "$OUT_DIR" && cd -- "$OUT_DIR" && pwd)"
if [[ "$CLEAN" -eq 1 ]]; then
  rm -f "$OUT_DIR/mfeprimer"
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

ART="$TMP_DIR/artifact.bin"
echo "Downloading MFEprimer artifact"
echo "URL: $URL"
curl -fL --retry 4 --retry-delay 1 --retry-connrefused -o "$ART" "$URL"

if [[ -n "$SHA256" ]]; then
  GOT="$(sha256sum "$ART" | awk '{print $1}')"
  if [[ "$GOT" != "$SHA256" ]]; then
    echo "Error: sha256 mismatch." >&2
    echo "Expected: $SHA256" >&2
    echo "Actual:   $GOT" >&2
    exit 1
  fi
fi

install_from="$ART"
case "$URL" in
  *.tar.gz|*.tgz)
    tar -xzf "$ART" -C "$TMP_DIR"
    cand="$(find "$TMP_DIR" -type f \( -name 'mfeprimer' -o -name 'mfeprimer_*' -o -name 'mfeprimer-linux*' \) | head -n 1 || true)"
    if [[ -z "$cand" ]]; then
      echo "Error: unable to locate mfeprimer executable in downloaded tar archive." >&2
      exit 1
    fi
    install_from="$cand"
    ;;
  *.gz)
    if ! command -v gunzip >/dev/null 2>&1; then
      echo "Error: gunzip is required for .gz artifacts." >&2
      exit 1
    fi
    cp "$ART" "$TMP_DIR/mfeprimer.gz"
    gunzip "$TMP_DIR/mfeprimer.gz"
    install_from="$TMP_DIR/mfeprimer"
    ;;
  *.zip)
    if ! command -v unzip >/dev/null 2>&1; then
      echo "Error: unzip is required for zip artifacts." >&2
      exit 1
    fi
    unzip -q "$ART" -d "$TMP_DIR/unzip"
    cand="$(find "$TMP_DIR/unzip" -type f \( -name 'mfeprimer' -o -name 'mfeprimer_*' -o -name 'mfeprimer-linux*' \) | head -n 1 || true)"
    if [[ -z "$cand" ]]; then
      echo "Error: unable to locate mfeprimer executable in downloaded zip archive." >&2
      exit 1
    fi
    install_from="$cand"
    ;;
esac

install -m 0755 "$install_from" "$OUT_DIR/mfeprimer"
echo "Done. Installed: $OUT_DIR/mfeprimer"
