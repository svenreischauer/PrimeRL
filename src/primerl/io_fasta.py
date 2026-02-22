"""Simple FASTA readers for migration workflows."""

from __future__ import annotations


def read_first_fasta_sequence(text: str) -> str:
    seq_lines: list[str] = []
    started = False
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if started and seq_lines:
                break
            started = True
            continue
        if started:
            seq_lines.append(line)
    return "".join(seq_lines)
