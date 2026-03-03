"""Headless CLI for primerl Python migration workflows."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Sequence

from .ensembl_adapter import (
    build_lookup_symbol_url,
    build_sequence_id_url,
    choose_preferred_transcript,
    extract_transcript_choices,
    map_ensembl_seq_type,
)
from .export_naming import build_order_oligos
from .golden import compare_summary, extract_summary
from .io_fasta import read_first_fasta_sequence
from .parity import compare_payloads, load_payload, run_json_command
from .platform_compat import subprocess_run
from .primer3_qpcr import (
    Primer3RunSettings,
    QpcrFilterSettings,
    clean_sequence,
    collect_qpcr_pairs_from_primer3,
    parse_primer3_kv_output,
    run_primer3_qpcr_output,
    sort_qpcr_pairs,
)
from .spidey_adapter import (
    analyze_spidey_output,
    build_spidey_args,
    extract_intron_exon_bounds,
    run_spidey_with_transport,
)


def _pd_stub(_s1: str, _s2: str, full: bool) -> float:
    return -2.0 if not full else -5.0


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _run_spidey_alignment(
    *,
    spidey_path: str,
    genomic_seq: str,
    mrna_seq: str,
    print_alignment: int,
    large_intron: bool,
) -> tuple[bool, str, str]:
    spidey_exec = Path(spidey_path)
    spidey_lib_dir = spidey_exec.parent / "lib"

    with tempfile.TemporaryDirectory() as td:
        dna_tmp = Path(td) / "dna.tmp.fasta"
        mrna_tmp = Path(td) / "mrna.tmp.fasta"
        dna_tmp.write_text(f">dna\n{genomic_seq}\n", encoding="utf-8")
        mrna_tmp.write_text(f">mrna\n{mrna_seq}\n", encoding="utf-8")

        args = build_spidey_args(
            spidey_exec=spidey_path,
            dna_tmp_path=str(dna_tmp),
            mrna_tmp_path=str(mrna_tmp),
            print_alignment=print_alignment,
            large_intron=large_intron,
        )

        def _transport(cmd: list[str]) -> tuple[int, str]:
            env = dict(os.environ)
            if spidey_lib_dir.exists() and spidey_lib_dir.is_dir():
                old_ld = str(env.get("LD_LIBRARY_PATH") or "").strip()
                env["LD_LIBRARY_PATH"] = (
                    f"{spidey_lib_dir}:{old_ld}" if old_ld else str(spidey_lib_dir)
                )
            proc = subprocess_run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            out = (proc.stdout or "")
            if proc.stderr:
                out = out + ("\n" if out else "") + proc.stderr
            return proc.returncode, out

        res = run_spidey_with_transport(args, _transport)
        return res.ok, res.output, res.error


def _resolve_spidey_bounds(args: argparse.Namespace) -> tuple[list[int], dict[str, object]]:
    base = [int(x) for x in args.boundary]
    if not args.run_spidey and not args.spidey_output:
        return sorted(set(base)), {"used": False, "source": "manual", "boundaries": sorted(set(base))}

    if args.run_spidey and args.spidey_output:
        raise SystemExit("Use only one of --run-spidey or --spidey-output")

    if args.spidey_output:
        spidey_txt = _read_text(args.spidey_output)
    else:
        if not args.spidey_path:
            raise SystemExit("--spidey-path is required when --run-spidey is used")
        if not args.genomic_fasta:
            raise SystemExit("--genomic-fasta is required when --run-spidey is used")
        mrna_seq = _resolve_template_seq(args)
        if not mrna_seq:
            raise SystemExit("Provide --template-seq or --mrna-fasta for --run-spidey")
        genomic_seq = clean_sequence(read_first_fasta_sequence(_read_text(args.genomic_fasta)))
        if not genomic_seq:
            raise SystemExit("Could not load genomic sequence from --genomic-fasta")
        ok, spidey_txt, err = _run_spidey_alignment(
            spidey_path=args.spidey_path,
            genomic_seq=genomic_seq,
            mrna_seq=mrna_seq,
            print_alignment=args.spidey_print_alignment,
            large_intron=args.spidey_large_intron,
        )
        if not ok:
            raise SystemExit(f"spidey run failed: {err}")

    status = analyze_spidey_output(spidey_txt)
    auto_bounds = extract_intron_exon_bounds(spidey_txt)
    merged = sorted(set(base + auto_bounds))
    info: dict[str, object] = {
        "used": True,
        "source": "spidey_output" if args.spidey_output else "run_spidey",
        "spidey_signature": status.has_signature,
        "full_identity_100": status.full_identity,
        "full_coverage_100": status.full_coverage,
        "auto_boundary_count": len(auto_bounds),
        "manual_boundary_count": len(base),
        "boundaries": merged,
    }
    # Backward-compatibility aliases for existing consumers.
    info["spidey_signature"] = info["spidey_signature"]
    return merged, info


def _parse_pair_items(items: Sequence[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for item in items:
        if ":" in item:
            fseq, rseq = item.split(":", 1)
        elif "," in item:
            fseq, rseq = item.split(",", 1)
        else:
            fseq, rseq = item, ""
        pairs.append((fseq.strip(), rseq.strip()))
    return pairs


def _cmd_order_export_preview(args: argparse.Namespace) -> int:
    pairs = _parse_pair_items(args.pair)
    rows = build_order_oligos(page=args.page, selected_pairs=pairs, gene=args.gene)
    payload = [r.__dict__ for r in rows]
    print(json.dumps(payload, indent=2))
    return 0


def _resolve_template_seq(args: argparse.Namespace) -> str:
    if args.template_seq:
        return clean_sequence(args.template_seq)
    if args.mrna_fasta:
        txt = _read_text(args.mrna_fasta)
        return clean_sequence(read_first_fasta_sequence(txt))
    return ""


def _cmd_qpcr_design(args: argparse.Namespace) -> int:
    if args.run_primer3:
        if not args.primer3_path:
            raise SystemExit("--primer3-path is required when --run-primer3 is used")

        template_seq = _resolve_template_seq(args)
        if not template_seq:
            raise SystemExit("Provide --template-seq or --mrna-fasta for --run-primer3")

        run_settings = Primer3RunSettings(
            min_tm_q=args.min_tm_q,
            max_tm_q=args.max_tm_q,
            max_diff_q=args.max_diff_q,
            pri_win_min_q=args.pri_win_min_q,
            pri_win_max_q=args.pri_win_max_q,
            min_ampsize_q=args.min_ampsize_q,
            max_ampsize_q=args.max_ampsize_q,
            exclude_gc=args.exclude_gc,
            exclude_clamp=args.exclude_clamp,
            min_gc=args.min_gc,
            max_gc=args.max_gc,
            monovalent_cation_conc=args.monovalent_cation_conc,
            mg_conc=args.mg_conc,
            dntp_conc=args.dntp_conc,
            oligo_conc=args.oligo_conc,
            num_return=args.num_return,
        )

        ok, output, err = run_primer3_qpcr_output(
            template_seq=template_seq,
            primer3_path=args.primer3_path,
            settings=run_settings,
        )
        if not ok:
            print(json.dumps({"error": err}, indent=2))
            return 2

        template_len = len(template_seq)
    else:
        if not args.primer3_output:
            raise SystemExit("--primer3-output is required unless --run-primer3 is used")
        output = _read_text(args.primer3_output)
        template_len = len(_resolve_template_seq(args)) if (_resolve_template_seq(args)) else args.template_len

    if template_len <= 0:
        raise SystemExit("Provide a positive template length via --template-len or template sequence/fasta")

    parsed = parse_primer3_kv_output(output)

    bounds, spidey_info = _resolve_spidey_bounds(args)

    settings = QpcrFilterSettings(
        exclude_rr_q=args.exclude_rr_q,
        run=args.run,
        repeat=args.repeat,
        ie_span=args.ie_span,
        ie_overlap=args.ie_overlap,
        exclude_ie=args.exclude_ie,
        intron_exon_bounds=tuple(bounds),
    )

    pairs, stats = collect_qpcr_pairs_from_primer3(
        parsed=parsed,
        template_len=template_len,
        settings=settings,
        primer_dimer_fn=_pd_stub,
    )

    pairs = sort_qpcr_pairs(pairs, sort_by=args.sort_by)

    if args.max_pairs is not None and args.max_pairs >= 0:
        pairs = pairs[: args.max_pairs]

    spidey_source = "spidey_output" if spidey_info.get("source") == "spidey_output" else "run_spidey"
    spidey_info = dict(spidey_info)
    spidey_info["source"] = spidey_source

    payload = {
        "stats": stats.__dict__,
        "returned_pairs": len(pairs),
        "spidey": spidey_info,
        "pairs": [p.to_legacy_row() for p in pairs],
    }
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_ensembl_fetch(args: argparse.Namespace) -> int:
    seq_type = map_ensembl_seq_type(args.seq_type)
    lookup_url = build_lookup_symbol_url(args.species, args.gene)
    out: dict[str, object] = {
        "lookup_url": lookup_url,
        "mapped_seq_type": seq_type,
    }

    if args.transcript_id:
        out["sequence_url"] = build_sequence_id_url(args.transcript_id, seq_type)

    if args.lookup_json:
        payload = json.loads(_read_text(args.lookup_json))
        choices = extract_transcript_choices(payload)
        best = choose_preferred_transcript(choices)
        out["transcript_count"] = len(choices)
        out["preferred_transcript"] = best.__dict__ if best else None
        out["longest_transcript"] = best.__dict__ if best else None

    print(json.dumps(out, indent=2))
    return 0


def _cmd_perl_parity(args: argparse.Namespace) -> int:
    if bool(args.perl_json) == bool(args.perl_cmd):
        raise SystemExit("Provide exactly one of --perl-json or --perl-cmd")
    if bool(args.python_json) == bool(args.python_cmd):
        raise SystemExit("Provide exactly one of --python-json or --python-cmd")

    perl_payload = load_payload(args.perl_json) if args.perl_json else run_json_command(args.perl_cmd)
    python_payload = load_payload(args.python_json) if args.python_json else run_json_command(args.python_cmd)
    result = compare_payloads(perl_payload, python_payload, top_n=args.top_n)
    print(json.dumps(result.to_dict(), indent=2))
    return 0


def _cmd_gui(_args: argparse.Namespace) -> int:
    from .gui import launch_gui

    return launch_gui()


def _load_payload_from_args(json_path: str, command: str) -> dict[str, object]:
    if bool(json_path) == bool(command):
        raise SystemExit("Provide exactly one of JSON path or command input")
    raw = load_payload(json_path) if json_path else run_json_command(command)
    return dict(raw)


def _cmd_golden_write(args: argparse.Namespace) -> int:
    payload = _load_payload_from_args(args.current_json, args.current_cmd)
    summary = extract_summary(payload)
    out = {"summary": summary}
    Path(args.output).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


def _cmd_golden_check(args: argparse.Namespace) -> int:
    payload = _load_payload_from_args(args.current_json, args.current_cmd)
    current_summary = extract_summary(payload)

    golden_raw = load_payload(args.golden_json)
    golden_summary = golden_raw.get("summary")
    if not isinstance(golden_summary, dict):
        golden_summary = extract_summary(golden_raw)

    report = compare_summary(current_summary, dict(golden_summary))
    report["current_summary"] = current_summary
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="primerl")
    sub = parser.add_subparsers(dest="command", required=True)

    p_export = sub.add_parser("order-export-preview", help="Preview export oligo names/rows")
    p_export.add_argument("--page", required=True, choices=["qpcr", "seq", "pd", "bis"])
    p_export.add_argument("--gene", required=True)
    p_export.add_argument(
        "--pair",
        action="append",
        default=[],
        help="Primer pair as F:R (or F,R). Repeat for multiple pairs.",
    )
    p_export.set_defaults(func=_cmd_order_export_preview)

    p_qpcr = sub.add_parser("qpcr-design", help="Parse Primer3 output and collect qPCR pairs")
    p_qpcr.add_argument("--run-primer3", action="store_true", help="Run primer3_core directly before parsing")
    p_qpcr.add_argument("--primer3-path", default="")
    p_qpcr.add_argument("--primer3-output", default="")
    p_qpcr.add_argument("--mrna-fasta", default="")
    p_qpcr.add_argument("--template-len", type=int, default=0)
    p_qpcr.add_argument("--template-seq", default="")
    p_qpcr.add_argument("--max-pairs", type=int, default=None, help="Limit number of output pairs")
    p_qpcr.add_argument(
        "--sort-by",
        default="perl_default",
        choices=["perl_default", "full_dimer", "pd_score", "amp_size", "primer3_order"],
        help="Pair ranking strategy before output limiting",
    )
    p_qpcr.add_argument("--exclude-rr-q", action="store_true")
    p_qpcr.add_argument("--run", type=int, default=4)
    p_qpcr.add_argument("--repeat", type=int, default=4)
    p_qpcr.add_argument("--ie-span", action="store_true")
    p_qpcr.add_argument("--ie-overlap", action="store_true")
    p_qpcr.add_argument("--exclude-ie", type=int, default=0)
    p_qpcr.add_argument("--boundary", action="append", type=int, default=[])
    p_qpcr.add_argument(
        "--run-spidey",
        "--run-spidey",
        dest="run_spidey",
        action="store_true",
        help="Run spidey and auto-extract intron/exon boundaries (legacy --run-spidey accepted)",
    )
    p_qpcr.add_argument(
        "--spidey-output",
        "--spidey-output",
        dest="spidey_output",
        default="",
        help="Parse boundaries from existing spidey/Spidey output text",
    )
    p_qpcr.add_argument(
        "--spidey-path",
        "--spidey-path",
        dest="spidey_path",
        default="",
        help="Path to spidey executable for --run-spidey mode",
    )
    p_qpcr.add_argument("--genomic-fasta", default="", help="Genomic FASTA input for --run-spidey mode")
    p_qpcr.add_argument(
        "--spidey-print-alignment",
        "--spidey-print-alignment",
        dest="spidey_print_alignment",
        type=int,
        default=1,
        help="Alignment print flag forwarded to selected backend",
    )
    p_qpcr.add_argument(
        "--spidey-large-intron",
        "--spidey-large-intron",
        dest="spidey_large_intron",
        action="store_true",
        help="Enable large-intron mode when using Spidey backend",
    )

    # Primer3 run settings (Perl-aligned defaults)
    p_qpcr.add_argument("--min-tm-q", type=float, default=58.0)
    p_qpcr.add_argument("--max-tm-q", type=float, default=62.0)
    p_qpcr.add_argument("--max-diff-q", type=float, default=2.0)
    p_qpcr.add_argument("--pri-win-min-q", type=int, default=20)
    p_qpcr.add_argument("--pri-win-max-q", type=int, default=24)
    p_qpcr.add_argument("--min-ampsize-q", type=int, default=100)
    p_qpcr.add_argument("--max-ampsize-q", type=int, default=300)
    p_qpcr.add_argument("--exclude-gc", action=argparse.BooleanOptionalAction, default=True)
    p_qpcr.add_argument("--exclude-clamp", action=argparse.BooleanOptionalAction, default=True)
    p_qpcr.add_argument("--min-gc", type=int, default=40)
    p_qpcr.add_argument("--max-gc", type=int, default=60)
    p_qpcr.add_argument("--monovalent-cation-conc", type=float, default=50.0)
    p_qpcr.add_argument("--mg-conc", type=float, default=1.5)
    p_qpcr.add_argument("--dntp-conc", type=float, default=0.2)
    p_qpcr.add_argument("--oligo-conc", type=float, default=200.0)
    p_qpcr.add_argument("--num-return", type=int, default=10000)

    p_qpcr.set_defaults(func=_cmd_qpcr_design)

    p_ens = sub.add_parser("ensembl-fetch", help="Build Ensembl URLs and transcript preselection")
    p_ens.add_argument("--species", required=True)
    p_ens.add_argument("--gene", required=True)
    p_ens.add_argument("--seq-type", default="cdna")
    p_ens.add_argument("--transcript-id", default="")
    p_ens.add_argument("--lookup-json", default="")
    p_ens.set_defaults(func=_cmd_ensembl_fetch)

    p_parity = sub.add_parser("perl-parity", help="Compare Perl and Python qPCR JSON outputs")
    p_parity.add_argument("--perl-json", default="")
    p_parity.add_argument("--python-json", default="")
    p_parity.add_argument("--perl-cmd", default="")
    p_parity.add_argument("--python-cmd", default="")
    p_parity.add_argument("--top-n", type=int, default=100)
    p_parity.set_defaults(func=_cmd_perl_parity)

    p_gui = sub.add_parser("gui", help="Launch minimal cross-platform qPCR GUI shell")
    p_gui.set_defaults(func=_cmd_gui)

    p_golden_write = sub.add_parser("golden-write", help="Write golden summary baseline from qPCR JSON payload")
    p_golden_write.add_argument("--current-json", default="")
    p_golden_write.add_argument("--current-cmd", default="")
    p_golden_write.add_argument("--output", required=True)
    p_golden_write.set_defaults(func=_cmd_golden_write)

    p_golden_check = sub.add_parser("golden-check", help="Compare current qPCR payload summary against golden baseline")
    p_golden_check.add_argument("--current-json", default="")
    p_golden_check.add_argument("--current-cmd", default="")
    p_golden_check.add_argument("--golden-json", required=True)
    p_golden_check.set_defaults(func=_cmd_golden_check)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
