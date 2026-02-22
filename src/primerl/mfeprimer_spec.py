"""Helpers for MFEprimer transcriptome specificity command arguments."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Callable

DEFAULT_SPEC_PARAMS_RAW = "-k 9 --misMatch 1"
DEFAULT_SPEC_PARAM_TOKENS = ["-k", "9", "--misMatch", "1"]
SOFT_SPEC_PARAMS_RAW = "-k 9 --misMatch 1"
SOFT_SPEC_PARAM_TOKENS = ["-k", "9", "--misMatch", "1"]
STRICT_SPEC_PARAMS_RAW = "-k 8 --misMatch 1"
STRICT_SPEC_PARAM_TOKENS = ["-k", "8", "--misMatch", "1"]

SPEC_PRESET_STRICT = "Strict"
SPEC_PRESET_SOFT = "Standard"

_ALLOWED_FLAGS = {"-k", "--misMatch", "-s", "-S"}
_FORBIDDEN_REQUIRED_FLAGS = {"-i", "-d", "-o"}
_FORBIDDEN_FLAGS = _FORBIDDEN_REQUIRED_FLAGS | {"-c"}
_FORBIDDEN_SUBCOMMANDS = {"spec", "dimer", "index"}


def parse_spec_param_tokens(raw: str) -> tuple[list[str], str | None]:
    """Parse a user-provided raw spec parameter string.

    Returns validated tokens and optional warning text. On parse/validation
    error, returns default tokens and a warning message.
    """

    txt = str(raw or "").strip()
    if not txt:
        return list(DEFAULT_SPEC_PARAM_TOKENS), None

    try:
        tokens = shlex.split(txt, posix=True)
    except ValueError:
        return (
            list(DEFAULT_SPEC_PARAM_TOKENS),
            f"Invalid specificity parameter syntax; using defaults: {DEFAULT_SPEC_PARAMS_RAW}.",
        )

    if not tokens:
        return list(DEFAULT_SPEC_PARAM_TOKENS), None

    out: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        tok_l = tok.lower()
        if tok_l in _FORBIDDEN_SUBCOMMANDS:
            return (
                list(DEFAULT_SPEC_PARAM_TOKENS),
                f"Specificity parameters cannot include a subcommand; using defaults: {DEFAULT_SPEC_PARAMS_RAW}.",
            )
        if tok in _FORBIDDEN_FLAGS:
            return (
                list(DEFAULT_SPEC_PARAM_TOKENS),
                f"Specificity parameters cannot override -i/-d/-o/-c; using defaults: {DEFAULT_SPEC_PARAMS_RAW}.",
            )

        matched_flag = ""
        matched_value = ""
        for flag in _ALLOWED_FLAGS:
            if tok.startswith(flag + "="):
                matched_flag = flag
                matched_value = tok.split("=", 1)[1]
                break
        if matched_flag:
            if matched_value == "":
                return (
                    list(DEFAULT_SPEC_PARAM_TOKENS),
                    f"Specificity parameter {matched_flag} requires a value; using defaults: {DEFAULT_SPEC_PARAMS_RAW}.",
                )
            out.extend([matched_flag, matched_value])
            i += 1
            continue

        if tok not in _ALLOWED_FLAGS:
            return (
                list(DEFAULT_SPEC_PARAM_TOKENS),
                f"Unsupported specificity flag '{tok}'; using defaults: {DEFAULT_SPEC_PARAMS_RAW}.",
            )
        if i + 1 >= len(tokens):
            return (
                list(DEFAULT_SPEC_PARAM_TOKENS),
                f"Specificity parameter {tok} requires a value; using defaults: {DEFAULT_SPEC_PARAMS_RAW}.",
            )

        out.extend([tok, tokens[i + 1]])
        i += 2

    return out, None


def resolve_spec_param_tokens(raw: str, on_error: Callable[[str], None] | None = None) -> list[str]:
    tokens, warning = parse_spec_param_tokens(raw)
    if warning and on_error is not None:
        on_error(warning)
    return tokens


def _token_value(tokens: list[str], flag: str) -> str:
    for i in range(0, len(tokens) - 1, 2):
        if tokens[i] == flag:
            return str(tokens[i + 1])
    return ""


def preset_from_spec_param_tokens(tokens: list[str]) -> str:
    k_val = _token_value(tokens, "-k")
    mm_val = _token_value(tokens, "--misMatch")
    if k_val == "9" and mm_val == "1":
        return SPEC_PRESET_SOFT
    return SPEC_PRESET_STRICT


def preset_from_spec_param_raw(raw: str) -> str:
    tokens, _warning = parse_spec_param_tokens(raw)
    return preset_from_spec_param_tokens(tokens)


def spec_param_raw_for_preset(preset: str) -> str:
    p = str(preset or "").strip().lower()
    if p in {"soft", "standard"}:
        return SOFT_SPEC_PARAMS_RAW
    if p == "strict":
        return STRICT_SPEC_PARAMS_RAW
    return DEFAULT_SPEC_PARAMS_RAW


def build_mfeprimer_spec_cmd(
    exe: Path,
    inp: Path,
    db: Path,
    out: Path,
    min_amp_size: int,
    max_amp_size: int,
    threads_per_job: int,
    spec_extra_args: list[str] | None = None,
    snp_bed_path: str = "",
    snp_records_loaded: int = 0,
) -> list[str]:
    cmd = [
        str(exe),
        "spec",
        "-i",
        str(inp),
        "-d",
        str(db),
        "-o",
        str(out),
        "-s",
        str(max(0, int(min_amp_size))),
        "-S",
        str(max(int(min_amp_size), int(max_amp_size))),
        "-c",
        str(max(1, int(threads_per_job))),
    ]
    cmd.extend(list(spec_extra_args) if spec_extra_args else list(DEFAULT_SPEC_PARAM_TOKENS))
    if snp_records_loaded:
        cmd.extend(["--snp", str(Path((snp_bed_path or "").strip()))])
    return cmd
