#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Build PrimeRL Debian package from Linux PyInstaller bundle.

Usage:
  ./release/scripts/build_deb.sh [options]

Options:
  --version <ver>      Package version (default: 1.2.0)
  --app-dir <dir>      Path to built app folder (default: release/PrimeRL_1.2_app_linux_x86_64_nodb/dist/PrimeRL)
  --clean              Remove previous deb build folder first
  -h, --help           Show this help

Notes:
  - The app directory should contain the PrimeRL executable and _internal payload.
  - The package installs to /opt/PrimeRL and adds /usr/bin/primerl launcher.
EOF
}

VERSION="1.2.0"
APP_DIR=""
CLEAN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="${2:-}"
      shift 2
      ;;
    --app-dir)
      APP_DIR="${2:-}"
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

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Error: Linux is required for .deb packaging." >&2
  exit 1
fi
if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "Error: dpkg-deb is required." >&2
  exit 1
fi

if [[ -z "$APP_DIR" ]]; then
  APP_DIR="$REPO_ROOT/release/PrimeRL_1.2_app_linux_x86_64_nodb/dist/PrimeRL"
fi
APP_DIR="$(cd -- "$APP_DIR" && pwd)"

if [[ ! -x "$APP_DIR/PrimeRL" ]]; then
  echo "Error: app executable not found at $APP_DIR/PrimeRL" >&2
  echo "Hint: build the Linux bundle first with release/scripts/build_linux_app.sh" >&2
  exit 1
fi

PKG_ROOT="$REPO_ROOT/release/PrimeRL_${VERSION}_deb_amd64"
STAGE="$PKG_ROOT/stage"
DIST="$PKG_ROOT/dist"
PKG_NAME="primerl"
DEB_PATH="$DIST/${PKG_NAME}_${VERSION}_amd64.deb"

if [[ "$CLEAN" -eq 1 && -d "$PKG_ROOT" ]]; then
  rm -rf "$PKG_ROOT"
fi
mkdir -p "$STAGE/DEBIAN" "$STAGE/opt/PrimeRL" "$STAGE/usr/bin" "$STAGE/usr/share/applications" "$DIST"

cp -a "$APP_DIR"/. "$STAGE/opt/PrimeRL/"

cat >"$STAGE/usr/bin/primerl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec /opt/PrimeRL/PrimeRL "$@"
EOF
chmod 0755 "$STAGE/usr/bin/primerl"

cat >"$STAGE/usr/share/applications/primerl.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=PrimeRL
Comment=qPCR primer design workspace
Exec=/usr/bin/primerl
Terminal=false
Categories=Science;Education;
EOF

cat >"$STAGE/DEBIAN/control" <<EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Section: science
Priority: optional
Architecture: amd64
Maintainer: PrimeRL Maintainers <maintainers@example.com>
Depends: libc6 (>= 2.31), libx11-6, libxext6, libxrender1, libxss1, libxtst6, libnss3, libasound2 | libasound2t64, zlib1g
Description: PrimeRL qPCR primer design workspace
 PrimeRL provides a GUI workspace for qPCR primer design, filtering, and
 transcriptome specificity checks using local tool binaries.
EOF

cat >"$STAGE/DEBIAN/postinst" <<'EOF'
#!/usr/bin/env bash
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications || true
fi
exit 0
EOF
chmod 0755 "$STAGE/DEBIAN/postinst"

echo "Building Debian package ..."
dpkg-deb --build --root-owner-group "$STAGE" "$DEB_PATH"

echo "Done: $DEB_PATH"
