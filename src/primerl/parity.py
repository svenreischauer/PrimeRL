"""Parity comparison helpers for Perl vs Python qPCR outputs."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ParityResult:
    perl_parsed: int
    python_parsed: int
    perl_returned: int
    python_returned: int
    compared_top_n: int
    overlap_count: int
    overlap_fraction: float
    only_perl_top_n: int
    only_python_top_n: int
    mean_rank_delta: float
    max_rank_delta: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "perl_parsed": self.perl_parsed,
            "python_parsed": self.python_parsed,
            "perl_returned": self.perl_returned,
            "python_returned": self.python_returned,
            "compared_top_n": self.compared_top_n,
            "overlap_count": self.overlap_count,
            "overlap_fraction": self.overlap_fraction,
            "only_perl_top_n": self.only_perl_top_n,
            "only_python_top_n": self.only_python_top_n,
            "mean_rank_delta": self.mean_rank_delta,
            "max_rank_delta": self.max_rank_delta,
        }


def load_payload(path: str) -> dict[str, Any]:
    txt = Path(path).read_text(encoding="utf-8")
    raw = json.loads(txt)
    if not isinstance(raw, dict):
        raise ValueError("Expected top-level JSON object")
    return raw


def run_json_command(command: str) -> dict[str, Any]:
    run_kwargs: dict[str, Any] = {
        "shell": True,
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        run_kwargs["creationflags"] = int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000))
    proc = subprocess.run(command, **run_kwargs)
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(f"Command failed ({proc.returncode}): {stderr}")
    out = (proc.stdout or "").strip()
    if not out:
        raise ValueError("Command returned empty stdout")
    raw = json.loads(out)
    if not isinstance(raw, dict):
        raise ValueError("Expected command stdout to be a JSON object")
    return raw


def _pair_key(row: list[Any]) -> str:
    # Stable identity for matching pair rank across implementations.
    f_seq = str(row[0]) if len(row) > 0 else ""
    r_seq = str(row[4]) if len(row) > 4 else ""
    amp = str(row[9]) if len(row) > 9 else ""
    return "|".join([f_seq.upper(), r_seq.upper(), amp])


def compare_payloads(perl_payload: dict[str, Any], python_payload: dict[str, Any], top_n: int = 100) -> ParityResult:
    perl_pairs = perl_payload.get("pairs") or []
    py_pairs = python_payload.get("pairs") or []
    if not isinstance(perl_pairs, list) or not isinstance(py_pairs, list):
        raise ValueError("Both payloads must include list field 'pairs'")

    top_n_use = max(0, top_n)
    perl_top = perl_pairs[:top_n_use]
    py_top = py_pairs[:top_n_use]

    perl_rank = {_pair_key(p): i for i, p in enumerate(perl_top) if isinstance(p, list)}
    py_rank = {_pair_key(p): i for i, p in enumerate(py_top) if isinstance(p, list)}

    overlap_keys = set(perl_rank).intersection(py_rank)
    rank_deltas = [abs(perl_rank[k] - py_rank[k]) for k in overlap_keys]

    overlap_count = len(overlap_keys)
    compared = min(top_n_use, len(perl_pairs), len(py_pairs))
    overlap_fraction = (overlap_count / compared) if compared else 0.0
    mean_rank_delta = (sum(rank_deltas) / len(rank_deltas)) if rank_deltas else 0.0
    max_rank_delta = max(rank_deltas) if rank_deltas else 0

    return ParityResult(
        perl_parsed=int(((perl_payload.get("stats") or {}).get("parsed") or 0)),
        python_parsed=int(((python_payload.get("stats") or {}).get("parsed") or 0)),
        perl_returned=int(perl_payload.get("returned_pairs") or len(perl_pairs)),
        python_returned=int(python_payload.get("returned_pairs") or len(py_pairs)),
        compared_top_n=compared,
        overlap_count=overlap_count,
        overlap_fraction=round(overlap_fraction, 6),
        only_perl_top_n=max(0, len(set(perl_rank) - set(py_rank))),
        only_python_top_n=max(0, len(set(py_rank) - set(perl_rank))),
        mean_rank_delta=round(mean_rank_delta, 6),
        max_rank_delta=max_rank_delta,
    )

