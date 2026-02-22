"""Golden baseline helpers for regression checks."""

from __future__ import annotations

from typing import Any

DEFAULT_PATHS = (
    "stats.parsed",
    "stats.skipped_order",
    "stats.skipped_span",
    "stats.skipped_overlap",
    "returned_pairs",
    "spidey.used",
    "spidey.source",
    "spidey.spidey_signature",
    "spidey.full_identity_100",
    "spidey.full_coverage_100",
    "spidey.auto_boundary_count",
    "spidey.manual_boundary_count",
    "spidey.boundaries",
)


def _get_path(obj: dict[str, Any], path: str) -> Any:
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        if part in cur:
            cur = cur[part]
            continue
        # Compatibility with pre-spidey payloads/baselines.
        if part == "spidey" and "spidey" in cur:
            cur = cur["spidey"]
            continue
        if part == "spidey_signature" and "spidey_signature" in cur:
            cur = cur["spidey_signature"]
            continue
        return None
    return cur


def extract_summary(payload: dict[str, Any], paths: tuple[str, ...] = DEFAULT_PATHS) -> dict[str, Any]:
    return {p: _get_path(payload, p) for p in paths}


def compare_summary(current: dict[str, Any], golden: dict[str, Any]) -> dict[str, Any]:
    diffs: dict[str, dict[str, Any]] = {}
    keys = sorted(set(current.keys()).union(golden.keys()))
    for k in keys:
        cv = current.get(k)
        gv = golden.get(k)
        if cv != gv:
            diffs[k] = {"current": cv, "golden": gv}
    return {"pass": len(diffs) == 0, "diff_count": len(diffs), "differences": diffs}

