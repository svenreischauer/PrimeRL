"""Primer3 qPCR parsing and collection logic for primerl."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
from typing import Callable, Mapping


@dataclass(frozen=True)
class QpcrFilterSettings:
    exclude_rr_q: bool = False
    run: int = 4
    repeat: int = 4
    ie_span: bool = False
    ie_overlap: bool = False
    exclude_ie: int = 0
    intron_exon_bounds: tuple[int, ...] = ()


@dataclass(frozen=True)
class Primer3RunSettings:
    """Primer3 qPCR run settings aligned to Perl defaults."""

    min_tm_q: float = 58.0
    max_tm_q: float = 62.0
    max_diff_q: float = 2.0
    pri_win_min_q: int = 20
    pri_win_max_q: int = 24
    min_ampsize_q: int = 100
    max_ampsize_q: int = 300
    exclude_gc: bool = True
    exclude_clamp: bool = True
    min_gc: int = 40
    max_gc: int = 60
    monovalent_cation_conc: float = 50.0
    mg_conc: float = 1.5
    dntp_conc: float = 0.2
    oligo_conc: float = 200.0
    num_return: int = 10000


@dataclass(frozen=True)
class QpcrCollectStats:
    parsed: int
    skipped_repeat_run: int
    skipped_order: int
    skipped_span: int
    skipped_overlap: int


@dataclass(frozen=True)
class PrimerPair:
    seq_f: str
    pos_f: int
    len_f: int
    tm_f: str
    seq_r: str
    pos_r: int
    len_r: int
    tm_r: str
    realpos_r: int
    amp_size: int
    pd_score: str
    reserved_1: int = 0
    reserved_2: int = 0
    pd_score_full: str = "0.00"

    def to_legacy_row(self) -> list[object]:
        return [
            self.seq_f,
            self.pos_f,
            self.len_f,
            self.tm_f,
            self.seq_r,
            self.pos_r,
            self.len_r,
            self.tm_r,
            self.realpos_r,
            self.amp_size,
            self.pd_score,
            self.reserved_1,
            self.reserved_2,
            self.pd_score_full,
        ]


def _score_as_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def sort_qpcr_pairs(pairs: list[PrimerPair], sort_by: str = "perl_default") -> list[PrimerPair]:
    """Sort pairs for output display/ranking.

    Modes:
    - perl_default: mimic Perl two-step sort (`13` then `10`) using stable sorts
    - full_dimer: full dimer score (column 13) descending
    - pd_score: dimer score (column 10) descending
    - amp_size: amplicon size ascending
    - primer3_order: no sorting
    """
    rows = list(pairs)
    if sort_by == "primer3_order":
        return rows
    if sort_by == "full_dimer":
        return sorted(rows, key=lambda p: _score_as_float(p.pd_score_full), reverse=True)
    if sort_by == "pd_score":
        return sorted(rows, key=lambda p: _score_as_float(p.pd_score), reverse=True)
    if sort_by == "amp_size":
        return sorted(rows, key=lambda p: p.amp_size)

    # perl_default: first full dimer, then dimer score (stable)
    rows = sorted(rows, key=lambda p: _score_as_float(p.pd_score_full), reverse=True)
    rows = sorted(rows, key=lambda p: _score_as_float(p.pd_score), reverse=True)
    return rows


def clean_sequence(seq: str) -> str:
    return re.sub(r"[^ATCGatcg]", "", seq or "")


def build_qpcr_input_text(template_seq: str, settings: Primer3RunSettings) -> str:
    template = clean_sequence(template_seq)
    opt_tm = (settings.min_tm_q + settings.max_tm_q) / 2.0
    min_gc_use = settings.min_gc if settings.exclude_gc else 0
    max_gc_use = settings.max_gc if settings.exclude_gc else 100
    gc_clamp = 2 if settings.exclude_clamp else 0

    lines = [
        "SEQUENCE_ID=qpcr",
        f"SEQUENCE_TEMPLATE={template}",
        "PRIMER_TASK=generic",
        f"PRIMER_NUM_RETURN={settings.num_return}",
        "PRIMER_PICK_LEFT_PRIMER=1",
        "PRIMER_PICK_RIGHT_PRIMER=1",
        "PRIMER_PICK_INTERNAL_OLIGO=0",
        f"PRIMER_MIN_SIZE={settings.pri_win_min_q}",
        f"PRIMER_MAX_SIZE={settings.pri_win_max_q}",
        f"PRIMER_MIN_TM={settings.min_tm_q}",
        f"PRIMER_MAX_TM={settings.max_tm_q}",
        f"PRIMER_OPT_TM={opt_tm:.2f}",
        f"PRIMER_MAX_TM_DIFF={settings.max_diff_q}",
        f"PRIMER_PRODUCT_SIZE_RANGE={settings.min_ampsize_q}-{settings.max_ampsize_q}",
        f"PRIMER_MIN_GC={min_gc_use}",
        f"PRIMER_MAX_GC={max_gc_use}",
        f"PRIMER_GC_CLAMP={gc_clamp}",
        f"PRIMER_SALT_MONOVALENT={settings.monovalent_cation_conc}",
        f"PRIMER_SALT_DIVALENT={settings.mg_conc}",
        f"PRIMER_DNTP_CONC={settings.dntp_conc}",
        f"PRIMER_DNA_CONC={settings.oligo_conc}",
        "=",
    ]
    return "\n".join(lines) + "\n"


_ILLEGAL_INSTRUCTION_RETURN = 0xC000001D
_MISSING_MODULE_RETURN = 0xC0000135


def _format_primer3_error(returncode: int, stdout: str, stderr: str) -> str:
    if returncode == _ILLEGAL_INSTRUCTION_RETURN:
        return (
            "Primer3 exited with STATUS_ILLEGAL_INSTRUCTION (0xC000001D). "
            "The performance binaries ship CPU-specific optimizations that this machine "
            "does not support. Please switch back to the Original profile."
        )
    if returncode == _MISSING_MODULE_RETURN:
        return (
            "Primer3 cannot find its runtime libraries (libstdc++). "
            "Make sure the tool's DLLs are placed next to the executable."
        )
    return (stderr or stdout or "Primer3 execution failed").strip()


def _default_primer3_runner(primer3_path: str, input_text: str) -> tuple[int, str, str]:
    env = dict(os.environ)
    try:
        exe = Path(primer3_path).resolve()
        chain: list[Path] = []
        cur = exe.parent
        for _ in range(5):
            chain.append(cur)
            if cur.parent == cur:
                break
            cur = cur.parent
        seen: set[str] = set()
        prepend: list[str] = []
        for p in chain:
            s = str(p)
            key = s.lower()
            if p.exists() and key not in seen:
                prepend.append(s)
                seen.add(key)
        old_path = str(env.get("PATH") or "")
        env["PATH"] = os.pathsep.join(prepend + [old_path])
    except Exception:
        pass

    run_kwargs: dict[str, object] = {
        "input": input_text,
        "text": True,
        "capture_output": True,
        "check": False,
        "env": env,
    }
    if os.name == "nt":
        run_kwargs["creationflags"] = int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000))
    proc = subprocess.run([primer3_path], **run_kwargs)
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def run_primer3_qpcr_output(
    template_seq: str,
    primer3_path: str,
    settings: Primer3RunSettings,
    runner: Callable[[str, str], tuple[int, str, str]] | None = None,
) -> tuple[bool, str, str]:
    input_text = build_qpcr_input_text(template_seq, settings)
    run = runner or _default_primer3_runner
    code, stdout, stderr = run(primer3_path, input_text)
    if code != 0:
        err = _format_primer3_error(code, stdout, stderr)
        return False, "", err
    return True, stdout, ""


def parse_primer3_kv_output(output: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in (output or "").splitlines():
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key] = value
    return parsed


def _has_excluded_repeats_or_runs(seq: str, run: int, repeat: int) -> bool:
    run = max(1, int(run))
    repeat_real = max(0, int(repeat) - 1)

    run_pat = re.compile(rf"(C{{{run},}}|A{{{run},}}|G{{{run},}}|T{{{run},}})", re.IGNORECASE)
    if run_pat.search(seq):
        return True

    rep_pat = re.compile(rf"(.{{2,}})\1{{{repeat_real},}}")
    return bool(rep_pat.search(seq))


def collect_qpcr_pairs_from_primer3(
    parsed: Mapping[str, str],
    template_len: int,
    settings: QpcrFilterSettings,
    primer_dimer_fn: Callable[[str, str, bool], float],
) -> tuple[list[PrimerPair], QpcrCollectStats]:
    pairs: list[PrimerPair] = []
    i = 0
    skipped_span = 0
    skipped_overlap = 0
    skipped_repeat_run = 0
    skipped_order = 0

    while f"PRIMER_LEFT_{i}" in parsed and f"PRIMER_RIGHT_{i}" in parsed:
        lpos_s, llen_s = parsed[f"PRIMER_LEFT_{i}"].split(",", 1)
        rpos_s, rlen_s = parsed[f"PRIMER_RIGHT_{i}"].split(",", 1)

        lpos = int(lpos_s)
        llen = int(llen_s)
        rpos = int(rpos_s)
        rlen = int(rlen_s)

        seq_f = parsed.get(f"PRIMER_LEFT_{i}_SEQUENCE", "")
        seq_r = parsed.get(f"PRIMER_RIGHT_{i}_SEQUENCE", "")

        if settings.exclude_rr_q:
            if _has_excluded_repeats_or_runs(seq_f, settings.run, settings.repeat):
                skipped_repeat_run += 1
                i += 1
                continue
            if _has_excluded_repeats_or_runs(seq_r, settings.run, settings.repeat):
                skipped_repeat_run += 1
                i += 1
                continue

        pos_f = lpos
        len_f = llen
        realpos_r = rpos
        pos_r = template_len - rpos - 1
        len_r = rlen

        if not (realpos_r - len_r > pos_f + len_f):
            skipped_order += 1
            i += 1
            continue

        if settings.ie_span:
            qpcr_check = any(pos_f < b < realpos_r for b in settings.intron_exon_bounds)
            if not qpcr_check:
                skipped_span += 1
                i += 1
                continue

        if settings.ie_overlap and settings.exclude_ie:
            qpcr_check = False
            for b in settings.intron_exon_bounds:
                if pos_f < (b - settings.exclude_ie) and (b + settings.exclude_ie) < (pos_f + len_f):
                    qpcr_check = True
                if (realpos_r - len_r) < (b - settings.exclude_ie) and (b + settings.exclude_ie) < realpos_r:
                    qpcr_check = True
            if not qpcr_check:
                skipped_overlap += 1
                i += 1
                continue

        tm_f = float(parsed.get(f"PRIMER_LEFT_{i}_TM", "0"))
        tm_r = float(parsed.get(f"PRIMER_RIGHT_{i}_TM", "0"))

        amp_raw = parsed.get(f"PRIMER_PAIR_{i}_PRODUCT_SIZE")
        amp_size = int(amp_raw) if amp_raw and amp_raw.isdigit() else (realpos_r - pos_f)

        pair_any_key = f"PRIMER_PAIR_{i}_COMPL_ANY_TH"
        pair_end_key = f"PRIMER_PAIR_{i}_COMPL_END_TH"
        left_any_key = f"PRIMER_LEFT_{i}_SELF_ANY_TH"
        left_end_key = f"PRIMER_LEFT_{i}_SELF_END_TH"
        right_any_key = f"PRIMER_RIGHT_{i}_SELF_ANY_TH"
        right_end_key = f"PRIMER_RIGHT_{i}_SELF_END_TH"
        if (
            pair_any_key in parsed
            or pair_end_key in parsed
            or left_any_key in parsed
            or left_end_key in parsed
            or right_any_key in parsed
            or right_end_key in parsed
        ):
            # Map Primer3 thermodynamic fields to legacy dG-like sign/ranking:
            # - "extensible" dimer score uses END metrics (3' end-driven)
            # - "full" dimer score uses ANY metrics (global complementarity)
            ext_vals = [
                float(parsed.get(left_end_key, "0") or 0.0),
                float(parsed.get(pair_end_key, "0") or 0.0),
                float(parsed.get(right_end_key, "0") or 0.0),
            ]
            full_vals = [
                float(parsed.get(left_any_key, "0") or 0.0),
                float(parsed.get(pair_any_key, "0") or 0.0),
                float(parsed.get(right_any_key, "0") or 0.0),
            ]
            pd_score = min(-v for v in ext_vals)
            pd_score_full = min(-v for v in full_vals)
        else:
            pd_score = primer_dimer_fn(seq_f, seq_f, False)
            pd_score = min(pd_score, primer_dimer_fn(seq_f, seq_r, False))
            pd_score = min(pd_score, primer_dimer_fn(seq_r, seq_r, False))

            pd_score_full = primer_dimer_fn(seq_f, seq_f, True)
            pd_score_full = min(pd_score_full, primer_dimer_fn(seq_f, seq_r, True))
            pd_score_full = min(pd_score_full, primer_dimer_fn(seq_r, seq_r, True))

        pairs.append(
            PrimerPair(
                seq_f=seq_f,
                pos_f=pos_f,
                len_f=len_f,
                tm_f=f"{tm_f:.2f}",
                seq_r=seq_r,
                pos_r=pos_r,
                len_r=len_r,
                tm_r=f"{tm_r:.2f}",
                realpos_r=realpos_r,
                amp_size=amp_size,
                pd_score=f"{pd_score:.2f}",
                pd_score_full=f"{pd_score_full:.2f}",
            )
        )

        i += 1

    stats = QpcrCollectStats(
        parsed=i,
        skipped_repeat_run=skipped_repeat_run,
        skipped_order=skipped_order,
        skipped_span=skipped_span,
        skipped_overlap=skipped_overlap,
    )
    return pairs, stats



