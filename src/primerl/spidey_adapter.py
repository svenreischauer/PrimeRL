"""Spidey adapter and output parsing logic for primerl."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable


@dataclass(frozen=True)
class SpideyRunResult:
    ok: bool
    output: str
    error: str = ""


@dataclass(frozen=True)
class SpideyOutputStatus:
    has_signature: bool
    full_identity: bool
    full_coverage: bool


def build_spidey_args(
    spidey_exec: str,
    dna_tmp_path: str,
    mrna_tmp_path: str,
    print_alignment: int,
    large_intron: bool = False,
) -> list[str]:
    args = [
        spidey_exec,
        "-i",
        dna_tmp_path,
        "-m",
        mrna_tmp_path,
        "-p",
        str(print_alignment),
    ]
    if large_intron:
        args.append("-X")
    return args


def run_spidey_with_transport(
    args: list[str],
    transport: Callable[[list[str]], tuple[int, str]],
) -> SpideyRunResult:
    code, out = transport(args)
    if code != 0:
        return SpideyRunResult(ok=False, output=out or "", error=f"spidey failed with exit code {code}")
    return SpideyRunResult(ok=True, output=out or "")


def analyze_spidey_output(output: str) -> SpideyOutputStatus:
    txt = output or ""
    return SpideyOutputStatus(
        has_signature=("--SPIDEY" in txt),
        full_identity=bool(re.search(r"overall percent identity:\s*100\.0%", txt)),
        full_coverage=bool(re.search(r"mRNA coverage:\s*100%", txt)),
    )


def extract_intron_exon_bounds(output: str) -> list[int]:
    """Extract intron/exon boundaries from Spidey output.

    Mirrors Perl behavior:
    - collect second position from each '(mRNA)' range `start-end (mRNA)`
    - remove last boundary (end of mRNA)
    """
    bounds = [int(m.group(2)) for m in re.finditer(r"(\d+)-(\d+)\s*\(mRNA\)", output or "")]
    if bounds:
        bounds.pop()
    return bounds



