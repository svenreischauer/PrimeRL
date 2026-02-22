from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    src_dir = repo_root / "src"
    sys.path.insert(0, str(src_dir))
    from primerl.gui import launch_gui

    return int(launch_gui())


if __name__ == "__main__":
    raise SystemExit(main())

