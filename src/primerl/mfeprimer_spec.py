"""Helpers for MFEprimer transcriptome specificity arguments and indexes."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Callable

DEFAULT_SPEC_PARAMS_RAW = "--misMatch 1"
DEFAULT_SPEC_PARAM_TOKENS = ["--misMatch", "1"]

MFEPRIMER_INDEX_SUFFIX = ".primerqc.bin"

_ALLOWED_FLAGS = {"--misMatch", "-s", "-S"}
_FORBIDDEN_REQUIRED_FLAGS = {"-i", "-d", "-o"}
_FORBIDDEN_FLAGS = _FORBIDDEN_REQUIRED_FLAGS | {"-c"}
_FORBIDDEN_SUBCOMMANDS = {"spec", "dimer", "index"}


def find_mfeprimer_binary_index(fasta_path: Path) -> Path | None:
    """Return the MFEprimer 4.5.1 binary index used for auto-k queries."""

    index_path = Path(f"{fasta_path}{MFEPRIMER_INDEX_SUFFIX}")
    return index_path if index_path.is_file() else None


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
    ignored_k = False
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

        # MFEprimer 4.5.1 reads k from a binary index. Query k must match the
        # index, so discard values left in older PrimeRL settings instead of
        # risking a mismatched-index failure.
        if tok == "-k":
            if i + 1 >= len(tokens) or tokens[i + 1].startswith("-"):
                return (
                    list(DEFAULT_SPEC_PARAM_TOKENS),
                    f"Specificity parameter -k requires a value; using defaults: {DEFAULT_SPEC_PARAMS_RAW}.",
                )
            ignored_k = True
            i += 2
            continue
        if tok.startswith("-k="):
            if not tok.split("=", 1)[1]:
                return (
                    list(DEFAULT_SPEC_PARAM_TOKENS),
                    f"Specificity parameter -k requires a value; using defaults: {DEFAULT_SPEC_PARAMS_RAW}.",
                )
            ignored_k = True
            i += 1
            continue

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

    if not out:
        out = list(DEFAULT_SPEC_PARAM_TOKENS)
    warning = None
    if ignored_k:
        warning = "MFEprimer k is auto-detected from the database index; the saved -k value was ignored."
    return out, warning


def resolve_spec_param_tokens(raw: str, on_error: Callable[[str], None] | None = None) -> list[str]:
    tokens, warning = parse_spec_param_tokens(raw)
    if warning and on_error is not None:
        on_error(warning)
    return tokens


def normalize_spec_param_raw(raw: str) -> str:
    """Return validated settings text with legacy query-time k removed."""

    tokens, _warning = parse_spec_param_tokens(raw)
    return shlex.join(tokens)


def _without_query_k(tokens: list[str]) -> list[str]:
    """Defensively remove query-time k from already-tokenized arguments."""

    cleaned: list[str] = []
    i = 0
    while i < len(tokens):
        tok = str(tokens[i])
        if tok == "-k":
            i += 2
            continue
        if tok.startswith("-k="):
            i += 1
            continue
        cleaned.append(tok)
        i += 1
    return cleaned


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
    extra_args = list(spec_extra_args) if spec_extra_args else list(DEFAULT_SPEC_PARAM_TOKENS)
    cmd.extend(_without_query_k(extra_args))
    if snp_records_loaded:
        cmd.extend(["--snp", str(Path((snp_bed_path or "").strip()))])
    return cmd
