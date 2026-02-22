"""Ensembl REST adapter logic for primerl."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Callable
from urllib.parse import quote


BASE_URL = "https://rest.ensembl.org"


@dataclass(frozen=True)
class EnsemblError:
    message: str


@dataclass(frozen=True)
class EnsemblNoGeneFound:
    reason: str = "no_gene_found"


@dataclass(frozen=True)
class TranscriptChoice:
    transcript_id: str
    display_label: str
    length: int
    is_canonical: bool = False
    is_protein_coding: bool = False
    transcript_support_level: int = 99
    appris_rank: int = 999
    cds_length: int = 0


def normalize_species_name(species: str) -> str:
    return re.sub(r"\s+", "_", species.strip().lower())


def map_ensembl_seq_type(seq_type: str) -> str:
    mapping = {
        "coding": "cds",
        "utr5": "5utr",
        "utr3": "3utr",
    }
    return mapping.get(seq_type, seq_type)


def build_lookup_symbol_url(species: str, gene_symbol: str, expand: bool = True) -> str:
    species_norm = normalize_species_name(species)
    gene_enc = quote(gene_symbol, safe="")
    expand_flag = "?expand=1" if expand else ""
    return f"{BASE_URL}/lookup/symbol/{species_norm}/{gene_enc}{expand_flag}"


def build_sequence_id_url(transcript_id: str, seq_type: str) -> str:
    seq_enc = quote(seq_type, safe="")
    tx_enc = quote(transcript_id, safe="")
    return f"{BASE_URL}/sequence/id/{tx_enc}?type={seq_enc}"


def detect_lookup_no_gene(url: str, curl_stderr: str) -> bool:
    if "/lookup/symbol/" not in url:
        return False
    msg = (curl_stderr or "").lower()
    return bool(re.search(r"(400|not\s+found|no\s+object)", msg))


def decode_ensembl_json(text: str) -> tuple[bool, Any, str]:
    try:
        return True, json.loads(text), ""
    except json.JSONDecodeError as e:
        # Perl had a relaxed fallback; Python stdlib has no direct relaxed mode.
        # Keep explicit error surface so caller can persist response snippet.
        return False, None, str(e)


def fetch_json_with_transport(
    url: str,
    transport: Callable[[str], tuple[int, str]],
) -> Any | EnsemblError | EnsemblNoGeneFound:
    """Fetch + decode JSON through injected transport.

    transport(url) -> (exit_code, text_or_stderr)
    exit_code 0 means success payload in text_or_stderr.
    non-zero means stderr/error text in text_or_stderr.
    """
    code, payload = transport(url)
    if code != 0:
        if detect_lookup_no_gene(url, payload):
            return EnsemblNoGeneFound()
        return EnsemblError(f"curl failed to fetch from Ensembl. {payload}")

    ok, data, err = decode_ensembl_json(payload)
    if not ok:
        snippet = re.sub(r"\s+", " ", payload)[:200]
        err_compact = re.sub(r"\s+", " ", err)[:160]
        return EnsemblError(
            f"Unable to parse Ensembl response. {err_compact} Snippet: {snippet}"
        )

    return data


def _tx_length(tx: dict[str, Any]) -> int:
    length = tx.get("length")
    if isinstance(length, int) and length > 0:
        return length

    tr = tx.get("Translation")
    if isinstance(tr, dict):
        tlen = tr.get("length")
        if isinstance(tlen, int) and tlen > 0:
            return tlen

    start = tx.get("start")
    end = tx.get("end")
    if isinstance(start, int) and isinstance(end, int):
        return abs(end - start) + 1

    return 0


def _to_bool_flag(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _parse_tsl(v: Any) -> int:
    if isinstance(v, int):
        return max(1, min(99, v))
    txt = str(v or "").strip().lower()
    if not txt:
        return 99
    m = re.search(r"\b([1-9])\b", txt)
    if m:
        return int(m.group(1))
    return 99


def _parse_appris_rank(v: Any) -> int:
    txt = str(v or "").strip().lower()
    if not txt:
        return 999
    m_principal = re.search(r"principal\s*([0-9]*)", txt)
    if m_principal:
        num_txt = m_principal.group(1)
        num = int(num_txt) if num_txt.isdigit() else 1
        return max(0, num - 1)
    m_alternative = re.search(r"alternative\s*([0-9]*)", txt)
    if m_alternative:
        num_txt = m_alternative.group(1)
        num = int(num_txt) if num_txt.isdigit() else 1
        return 100 + max(0, num - 1)
    return 999


def _tx_cds_length(tx: dict[str, Any]) -> int:
    tr = tx.get("Translation")
    if isinstance(tr, dict):
        tlen = tr.get("length")
        if isinstance(tlen, int) and tlen > 0:
            return tlen
    return 0


def extract_transcript_choices(gene_payload: dict[str, Any]) -> list[TranscriptChoice]:
    out: list[TranscriptChoice] = []
    for tx in gene_payload.get("Transcript", []) or []:
        tid = tx.get("id")
        if not tid:
            continue
        label = f"{tid} {tx.get('display_name')}" if tx.get("display_name") else tid
        out.append(
            TranscriptChoice(
                transcript_id=tid,
                display_label=label,
                length=_tx_length(tx),
                is_canonical=_to_bool_flag(tx.get("is_canonical")),
                is_protein_coding=str(tx.get("biotype") or "").strip().lower() == "protein_coding",
                transcript_support_level=_parse_tsl(tx.get("transcript_support_level")),
                appris_rank=_parse_appris_rank(tx.get("appris")),
                cds_length=_tx_cds_length(tx),
            )
        )
    return out


def choose_longest_transcript(choices: list[TranscriptChoice]) -> TranscriptChoice | None:
    if not choices:
        return None
    return sorted(choices, key=lambda c: (-c.length, c.display_label))[0]


def choose_preferred_transcript(choices: list[TranscriptChoice]) -> TranscriptChoice | None:
    if not choices:
        return None
    return sorted(
        choices,
        key=lambda c: (
            0 if c.is_canonical else 1,
            0 if c.is_protein_coding else 1,
            int(c.transcript_support_level),
            int(c.appris_rank),
            -int(c.cds_length),
            -int(c.length),
            c.display_label,
        ),
    )[0]


