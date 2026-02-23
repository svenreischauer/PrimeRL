#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 not found." >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  python3 -m venv --system-site-packages .venv
fi

source .venv/bin/activate
python -m pip install --quiet --disable-pip-version-check ttkbootstrap openpyxl

has_spidey=0
if [[ -x "PrimeRL/tools/bin/spidey" || -x "tools/bin/spidey" ]]; then
  has_spidey=1
elif command -v spidey >/dev/null 2>&1; then
  has_spidey=1
fi

has_minimap2=0
if command -v minimap2 >/dev/null 2>&1; then
  has_minimap2=1
fi

if [[ "$has_spidey" -eq 0 && "$has_minimap2" -eq 0 ]]; then
  echo "Warning: neither spidey nor minimap2 was found. Alignment-backed boundary detection may fail." >&2
fi

PYTHONPATH=src python run_gui.py
