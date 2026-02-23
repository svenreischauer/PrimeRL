"""Cross-platform helpers for runtime/process behavior."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


IS_WINDOWS = os.name == "nt"
IS_MACOS = sys.platform == "darwin"
IS_APPLE_SILICON = IS_MACOS and (os.uname().machine == "arm64")
BIN_EXT = ".exe" if IS_WINDOWS else ""


def normalize_exec_name(path: str) -> str:
    p = Path(str(path or ""))
    name = p.name
    if name.lower().endswith(".exe"):
        name = name[:-4]
    return name.lower()


def candidate_exec_names(base_name: str) -> list[str]:
    base = str(base_name or "").strip()
    if not base:
        return []
    if base.lower().endswith(".exe"):
        out = [base, base[:-4]]
    else:
        out = [f"{base}{BIN_EXT}", base]
    seen: set[str] = set()
    deduped: list[str] = []
    for item in out:
        key = item.lower()
        if key in seen:
            continue
        deduped.append(item)
        seen.add(key)
    return deduped


def subprocess_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
    if IS_WINDOWS:
        flags = int(kwargs.get("creationflags", 0))
        flags |= int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000))
        kwargs["creationflags"] = flags
    return subprocess.run(*args, **kwargs)


def open_file(path: str) -> bool:
    target = str(path or "").strip()
    if not target:
        return False
    try:
        if IS_WINDOWS:
            os.startfile(target)  # type: ignore[attr-defined]
            return True
        cmd = ["open", target] if IS_MACOS else ["xdg-open", target]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return proc.returncode == 0
    except Exception:
        return False
