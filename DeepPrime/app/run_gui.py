from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    app_root = Path(__file__).resolve().parent
    src_dir = app_root / "src"
    sys.path.insert(0, str(src_dir))
    from deepprimerl.gui import launch_gui

    return int(launch_gui())


if __name__ == "__main__":
    raise SystemExit(main())
