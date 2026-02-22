"""Order-form naming and oligo row assembly logic.

Naming helpers:
- order_pair_tag
- build_order_oligos
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OligoRow:
    """One order-form row."""

    name: str
    sequence: str
    length: int


def order_pair_tag(page: str, pair_no: int) -> str:
    """Return per-page pair label used in exported oligo names."""
    if page == "qpcr":
        return f"qRT{pair_no}"
    if page == "seq":
        return f"seq{pair_no}"
    return str(pair_no)


def build_order_oligos(
    page: str,
    selected_pairs: list[tuple[str, str]],
    gene: str,
) -> list[OligoRow]:
    """Build export rows using current DeepPrime naming rules."""
    oligos: list[OligoRow] = []

    for idx, (fseq, rseq) in enumerate(selected_pairs, start=1):
        pair_tag = order_pair_tag(page, idx)

        fseq = fseq or ""
        rseq = rseq or ""

        oligos.append(
            OligoRow(
                name=f"{gene}_{pair_tag}F",
                sequence=fseq,
                length=len(fseq),
            )
        )

        if page == "seq" or rseq == "":
            continue

        oligos.append(
            OligoRow(
                name=f"{gene}_{pair_tag}R",
                sequence=rseq,
                length=len(rseq),
            )
        )

    return oligos

