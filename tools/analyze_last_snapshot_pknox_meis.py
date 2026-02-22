from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

REPO = Path(r"C:\Users\svenr\Documents\DeepPrimeRL\python_port")
SNAP = REPO / "DeepPrime" / "runtime" / "logs" / "last_postfilter_snapshot.json"
DB = REPO / "DeepPrime" / "databases" / "ensembl" / "Danio_rerio.GRCz11.cdna.all.fa"
MFE = REPO / "DeepPrime" / "tools" / "bin" / "mfeprimer.exe"

TARGETS = {
    "pknox1.2": "ENSDARG00000036542",
    "meis1a": "ENSDARG00000002937",
    "meis2a": "ENSDARG00000098240",
}

def norm_gid(raw: str) -> str:
    m = re.search(r"(ENS[A-Z]*G\d+)(?:\.\d+)?", (raw or "").upper())
    return m.group(1) if m else ""

if not SNAP.exists():
    raise SystemExit(f"Snapshot not found: {SNAP}")
if not DB.exists() or not MFE.exists():
    raise SystemExit("Required DB or mfeprimer executable missing")

snap = json.loads(SNAP.read_text(encoding="utf-8"))
rows = list(snap.get("rows") or [])
if not rows:
    raise SystemExit("Snapshot has no rows")

with tempfile.TemporaryDirectory() as td:
    tdp = Path(td)
    inp = tdp / "pairs.tsv"
    out = tdp / "spec.txt"
    inp.write_text("\n".join(f"p{i}\t{str(r[0])}\t{str(r[4])}" for i, r in enumerate(rows)) + "\n", encoding="utf-8")
    cmd = [
        str(MFE),
        "spec",
        "-i", str(inp),
        "-d", str(DB),
        "-o", str(out),
        "-s", str(int(snap.get("min_amp", 100))),
        "-S", str(int(snap.get("max_amp", 300))),
        "-c", "8",
        "-k", "9",
        "--misMatch", "0",
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    payload = out.read_text(encoding="utf-8", errors="replace") if out.exists() else ""
    if not payload.strip():
        payload = (p.stdout or "") + "\n" + (p.stderr or "")

amp_pat = re.compile(r"Amp\s+\d+:\s+p(\d+)_fp\s+\+\s+p(\d+)_rp\s+==>\s*(.+)", re.IGNORECASE)
pair_hits = {i: set() for i in range(len(rows))}
pair_amp = {i: 0 for i in range(len(rows))}
for m in amp_pat.finditer(payload):
    i1 = int(m.group(1)); i2 = int(m.group(2))
    if i1 != i2 or i1 not in pair_hits:
        continue
    pair_amp[i1] += 1
    desc = m.group(3)
    for gm in re.finditer(r"\bgene:([^\s]+)", desc, re.IGNORECASE):
        gid = norm_gid(gm.group(1))
        if gid:
            pair_hits[i1].add(gid)

print(f"Snapshot: {SNAP}")
print(f"Rows: {len(rows)}")
print("idx\tamp\thit_pknox\thit_meis1a\thit_meis2a\tfp\trp")
hit_any = 0
for i, row in enumerate(rows):
    hits = pair_hits.get(i, set())
    hp = 1 if TARGETS["pknox1.2"] in hits else 0
    hm1 = 1 if TARGETS["meis1a"] in hits else 0
    hm2 = 1 if TARGETS["meis2a"] in hits else 0
    if hp or hm1 or hm2:
        hit_any += 1
    print(f"{i+1}\t{pair_amp.get(i,0)}\t{hp}\t{hm1}\t{hm2}\t{str(row[0])}\t{str(row[4])}")

print("\nSUMMARY")
print(f"pairs_with_any_pknox_meis_hit={hit_any}")

