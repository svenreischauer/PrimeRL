from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _deepprime_root() -> Path:
    return _repo_root() / "DeepPrime"


def _pick_existing(candidates: Iterable[Path]) -> Path | None:
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


@dataclass
class AssetResult:
    key: str
    source: str
    destination: str
    mode: str
    status: str
    bytes: int
    note: str


def _stage_file(
    *,
    src: Path,
    dst: Path,
    mode: str,
    dry_run: bool,
    force: bool,
    fallback_copy: bool,
) -> tuple[str, int, str]:
    if not src.exists() or not src.is_file():
        return "missing", 0, "source file not found"
    if dst.exists() and not force:
        return "exists", dst.stat().st_size, "destination already exists"

    if dry_run:
        return "planned", src.stat().st_size, "dry run"

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and force:
        dst.unlink()

    if mode == "hardlink":
        try:
            os.link(str(src), str(dst))
            return "linked", dst.stat().st_size, ""
        except Exception as exc:
            if not fallback_copy:
                return "error", 0, f"hardlink failed: {exc}"
            shutil.copy2(src, dst)
            return "copied", dst.stat().st_size, "hardlink failed; copied instead"

    shutil.copy2(src, dst)
    return "copied", dst.stat().st_size, ""


def _sidecar_candidates(base: Path) -> list[Path]:
    # Keep only sidecars useful for reproducibility/index validation.
    names = [
        f"{base.name}.primerqc",
        f"{base.name}.primerqc.fai",
        f"{base.name}.fai",
        f"{base.name}.json",
        f"{base.name}.log",
    ]
    return [base.parent / n for n in names]


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage DeepPrime binaries and databases for installer prep.")
    parser.add_argument("--mode", choices=("hardlink", "copy"), default="hardlink")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--fallback-copy", action="store_true", default=True)
    parser.add_argument("--manifest", default=str(_deepprime_root() / "release" / "asset_manifest.json"))
    args = parser.parse_args()

    repo = _repo_root()
    deep = _deepprime_root()
    ex = Path(r"C:\Users\svenr\Documents\DeepPrimeRL\Example sequences")
    refseq = ex / "refseq"
    wip = Path(r"C:\Users\svenr\Documents\DeepPrimeRL\wip")
    p3_261 = Path(r"C:\Users\svenr\Documents\DeepPrimeRL\primer3\primer3-2.6.1\src")
    p3_260 = Path(r"C:\Users\svenr\Documents\DeepPrimeRL\primer3\primer3-2.6.0\src")

    assets: dict[str, tuple[list[Path], Path]] = {
        "primer3_core": (
            [
                deep / "tools" / "bin" / "primer3_core.exe",
                wip / "primer3_core_v2.6.1_AVX2_FMA3.exe",
                p3_261 / "primer3_core.exe",
                p3_260 / "primer3_core.exe",
            ],
            deep / "tools" / "bin" / "primer3_core.exe",
        ),
        "spidey": (
            [
                deep / "tools" / "bin" / "Spidey.exe",
                wip / "Spidey_AVX2_FMA3.exe",
                wip / "Spidey.exe",
                Path(r"C:\Users\svenr\Documents\DeepPrimeRL\build\Spidey.exe"),
                Path(r"C:\Users\svenr\Documents\DeepPrimeRL\clean\build\Spidey.exe"),
            ],
            deep / "tools" / "bin" / "Spidey.exe",
        ),
        "ntthal": (
            [
                deep / "tools" / "bin" / "ntthal.exe",
                wip / "ntthal_v2.6.1_AVX2_FMA3.exe",
                wip / "ntthal.exe",
                p3_261 / "ntthal.exe",
            ],
            deep / "tools" / "bin" / "ntthal.exe",
        ),
        "oligotm": (
            [
                deep / "tools" / "bin" / "oligotm.exe",
                wip / "oligotm_v2.6.1_AVX2_FMA3.exe",
                wip / "oligotm.exe",
                p3_261 / "oligotm.exe",
            ],
            deep / "tools" / "bin" / "oligotm.exe",
        ),
        "mfeprimer": (
            [
                deep / "tools" / "bin" / "mfeprimer.exe",
                repo / "tools" / "mfeprimer" / "mfeprimer.exe",
                Path(r"C:\Users\svenr\Documents\DeepPrimeRL\mfeprimer.exe"),
                wip / "mfeprimer.exe",
            ],
            deep / "tools" / "bin" / "mfeprimer.exe",
        ),
        "ensembl_cdna_fasta": (
            [
                deep / "databases" / "ensembl" / "Danio_rerio.GRCz11.cdna.all.fa",
                ex / "Danio_rerio.GRCz11.cdna.all.fa",
            ],
            deep / "databases" / "ensembl" / "Danio_rerio.GRCz11.cdna.all.fa",
        ),
        "refseq_rna_fasta": (
            [
                deep / "databases" / "refseq" / "Danio_rerio.RefSeq.rna.all.fa",
                refseq / "Danio_rerio.RefSeq.rna.all.fa",
            ],
            deep / "databases" / "refseq" / "Danio_rerio.RefSeq.rna.all.fa",
        ),
        "example_mrna": (
            [
                deep / "databases" / "ensembl" / "mRNA.fasta",
                ex / "mRNA.fasta",
            ],
            deep / "databases" / "ensembl" / "mRNA.fasta",
        ),
        "example_genomic": (
            [
                deep / "databases" / "ensembl" / "genomic.fasta",
                ex / "genomic.fasta",
            ],
            deep / "databases" / "ensembl" / "genomic.fasta",
        ),
    }

    results: list[AssetResult] = []
    for key, (cands, dst) in assets.items():
        src = _pick_existing(cands)
        if src is None:
            results.append(
                AssetResult(
                    key=key,
                    source="",
                    destination=str(dst),
                    mode=args.mode,
                    status="missing",
                    bytes=0,
                    note="no candidate source found",
                )
            )
            continue
        status, size, note = _stage_file(
            src=src,
            dst=dst,
            mode=args.mode,
            dry_run=args.dry_run,
            force=args.force,
            fallback_copy=args.fallback_copy,
        )
        results.append(
            AssetResult(
                key=key,
                source=str(src),
                destination=str(dst),
                mode=args.mode,
                status=status,
                bytes=size,
                note=note,
            )
        )
        if key in {"ensembl_cdna_fasta", "refseq_rna_fasta"} and src.exists():
            for side_src in _sidecar_candidates(src):
                if not side_src.exists() or not side_src.is_file():
                    continue
                side_dst = dst.parent / side_src.name
                s_status, s_size, s_note = _stage_file(
                    src=side_src,
                    dst=side_dst,
                    mode=args.mode,
                    dry_run=args.dry_run,
                    force=args.force,
                    fallback_copy=args.fallback_copy,
                )
                results.append(
                    AssetResult(
                        key=f"{key}:{side_src.name}",
                        source=str(side_src),
                        destination=str(side_dst),
                        mode=args.mode,
                        status=s_status,
                        bytes=s_size,
                        note=s_note,
                    )
                )

    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "deepprime_root": str(deep),
        "mode": args.mode,
        "dry_run": bool(args.dry_run),
        "results": [asdict(r) for r in results],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    ok = sum(1 for r in results if r.status in {"linked", "copied", "exists", "planned"})
    miss = sum(1 for r in results if r.status == "missing")
    err = sum(1 for r in results if r.status == "error")
    print(f"Manifest: {manifest_path}")
    print(f"Assets: ok={ok} missing={miss} error={err}")
    for r in results:
        print(f"[{r.status}] {r.key} -> {r.destination}")
    return 0 if err == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

