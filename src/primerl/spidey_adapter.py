"""Spidey adapter and output parsing logic for primerl."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable

from .platform_compat import normalize_exec_name


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


def _is_minimap2(exec_path: str) -> bool:
    return normalize_exec_name(exec_path) == "minimap2"


def _convert_minimap2_sam_to_spidey(sam_text: str) -> str:
    txt = str(sam_text or "")
    exons: list[tuple[int, int]] = []

    for line in txt.splitlines():
        if not line or line.startswith("@"):
            continue
        cols = line.split("\t")
        if len(cols) < 6:
            continue
        try:
            flag = int(cols[1])
        except Exception:
            continue

        # Filter unmapped (0x4), secondary (0x100), supplementary (0x800).
        if flag & 0x904:
            continue

        cigar = cols[5]
        if cigar == "*" or not cigar:
            continue

        q_pos = 1
        exon_start = q_pos
        cigar_ops = re.findall(r"(\d+)([MIDNSHP=X])", cigar)
        if not cigar_ops:
            continue
        for length_txt, op in cigar_ops:
            length = int(length_txt)
            if op in {"M", "I", "=", "X", "S"}:
                q_pos += length
                continue
            if op == "N":
                exon_end = q_pos - 1
                if exon_end >= exon_start:
                    exons.append((exon_start, exon_end))
                exon_start = q_pos
                continue
            # D/H/P consume no query positions.
        exon_end = q_pos - 1
        if exon_end >= exon_start:
            exons.append((exon_start, exon_end))

        # Only first primary alignment should be considered.
        break

    out = ["minimap2 fallback report"]
    for i, (start, end) in enumerate(exons, start=1):
        out.append(f"Exon {i}: {start}-{end} (mRNA)")
    return "\n".join(out)


def build_spidey_args(
    spidey_exec: str,
    dna_tmp_path: str,
    mrna_tmp_path: str,
    print_alignment: int,
    large_intron: bool = False,
) -> list[str]:
    if _is_minimap2(spidey_exec):
        return [
            spidey_exec,
            "-x",
            "splice",
            "-a",
            "--secondary=no",
            dna_tmp_path,
            mrna_tmp_path,
        ]

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
    output = out or ""
    if args and _is_minimap2(args[0]):
        output = _convert_minimap2_sam_to_spidey(output)
    return SpideyRunResult(ok=True, output=output)


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


