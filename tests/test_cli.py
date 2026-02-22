import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from primerl.cli import main


class CliTests(unittest.TestCase):
    def _run(self, argv: list[str]) -> tuple[int, dict]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(argv)
        out = buf.getvalue().strip()
        return rc, json.loads(out)

    def test_order_export_preview(self) -> None:
        rc, payload = self._run(
            [
                "order-export-preview",
                "--page",
                "qpcr",
                "--gene",
                "ACTB",
                "--pair",
                "AAAA:TTTT",
            ]
        )
        self.assertEqual(rc, 0)
        self.assertEqual(payload[0]["name"], "ACTB_qRT1F")
        self.assertEqual(payload[1]["name"], "ACTB_qRT1R")

    def test_qpcr_design_from_output_file(self) -> None:
        content = "\n".join(
            [
                "PRIMER_LEFT_0=10,20",
                "PRIMER_RIGHT_0=80,20",
                "PRIMER_LEFT_0_SEQUENCE=AAAA",
                "PRIMER_RIGHT_0_SEQUENCE=TTTT",
                "PRIMER_LEFT_0_TM=60",
                "PRIMER_RIGHT_0_TM=61",
                "PRIMER_PAIR_0_PRODUCT_SIZE=70",
            ]
        )
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "primer3.out"
            p.write_text(content, encoding="utf-8")
            rc, payload = self._run(
                [
                    "qpcr-design",
                    "--primer3-output",
                    str(p),
                    "--template-len",
                    "100",
                ]
            )
        self.assertEqual(rc, 0)
        self.assertEqual(payload["stats"]["parsed"], 1)
        self.assertEqual(len(payload["pairs"]), 1)
        self.assertEqual(payload["returned_pairs"], 1)

    def test_qpcr_design_max_pairs(self) -> None:
        content = "\n".join(
            [
                "PRIMER_LEFT_0=10,20",
                "PRIMER_RIGHT_0=80,20",
                "PRIMER_LEFT_0_SEQUENCE=AAAA",
                "PRIMER_RIGHT_0_SEQUENCE=TTTT",
                "PRIMER_LEFT_0_TM=60",
                "PRIMER_RIGHT_0_TM=61",
                "PRIMER_LEFT_1=12,20",
                "PRIMER_RIGHT_1=85,20",
                "PRIMER_LEFT_1_SEQUENCE=CCCC",
                "PRIMER_RIGHT_1_SEQUENCE=GGGG",
                "PRIMER_LEFT_1_TM=60",
                "PRIMER_RIGHT_1_TM=61",
            ]
        )
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "primer3.out"
            p.write_text(content, encoding="utf-8")
            rc, payload = self._run(
                [
                    "qpcr-design",
                    "--primer3-output",
                    str(p),
                    "--template-len",
                    "100",
                    "--max-pairs",
                    "1",
                    "--sort-by",
                    "amp_size",
                ]
            )
        self.assertEqual(rc, 0)
        self.assertEqual(payload["stats"]["parsed"], 2)
        self.assertEqual(payload["returned_pairs"], 1)
        self.assertEqual(len(payload["pairs"]), 1)
        # With amp_size sort, the smaller amplicon (pair 0) is selected first.
        self.assertEqual(payload["pairs"][0][0], "AAAA")

    def test_qpcr_design_run_primer3_mode(self) -> None:
        fake_output = "\n".join(
            [
                "PRIMER_LEFT_0=10,20",
                "PRIMER_RIGHT_0=80,20",
                "PRIMER_LEFT_0_SEQUENCE=AAAA",
                "PRIMER_RIGHT_0_SEQUENCE=TTTT",
                "PRIMER_LEFT_0_TM=60",
                "PRIMER_RIGHT_0_TM=61",
            ]
        )
        with patch("primerl.cli.run_primer3_qpcr_output", return_value=(True, fake_output, "")):
            rc, payload = self._run(
                [
                    "qpcr-design",
                    "--run-primer3",
                    "--primer3-path",
                    "primer3_core.exe",
                    "--template-seq",
                    "ACGT" * 40,
                ]
            )
        self.assertEqual(rc, 0)
        self.assertEqual(payload["stats"]["parsed"], 1)

    def test_qpcr_design_with_spidey_output_boundaries(self) -> None:
        primer3_content = "\n".join(
            [
                "PRIMER_LEFT_0=10,20",
                "PRIMER_RIGHT_0=180,20",
                "PRIMER_LEFT_0_SEQUENCE=AAAA",
                "PRIMER_RIGHT_0_SEQUENCE=TTTT",
                "PRIMER_LEFT_0_TM=60",
                "PRIMER_RIGHT_0_TM=61",
                "PRIMER_PAIR_0_PRODUCT_SIZE=170",
            ]
        )
        spidey_content = "\n".join(
            [
                "--SPIDEY",
                "overall percent identity: 100.0%",
                "mRNA coverage: 100%",
                "Exon 1: 1-100 (mRNA)",
                "Exon 2: 101-200 (mRNA)",
            ]
        )
        with tempfile.TemporaryDirectory() as td:
            p3 = Path(td) / "primer3.out"
            sp = Path(td) / "spidey.out"
            p3.write_text(primer3_content, encoding="utf-8")
            sp.write_text(spidey_content, encoding="utf-8")
            rc, payload = self._run(
                [
                    "qpcr-design",
                    "--primer3-output",
                    str(p3),
                    "--template-len",
                    "300",
                    "--ie-span",
                    "--spidey-output",
                    str(sp),
                ]
            )
        self.assertEqual(rc, 0)
        self.assertEqual(payload["stats"]["parsed"], 1)
        self.assertEqual(payload["returned_pairs"], 1)
        self.assertTrue(payload["spidey"]["used"])
        self.assertEqual(payload["spidey"]["auto_boundary_count"], 1)
        self.assertEqual(payload["spidey"]["boundaries"], [100])
        self.assertEqual(payload["spidey"]["source"], "spidey_output")

    def test_qpcr_design_run_spidey_mode_with_mock(self) -> None:
        primer3_content = "\n".join(
            [
                "PRIMER_LEFT_0=10,20",
                "PRIMER_RIGHT_0=180,20",
                "PRIMER_LEFT_0_SEQUENCE=AAAA",
                "PRIMER_RIGHT_0_SEQUENCE=TTTT",
                "PRIMER_LEFT_0_TM=60",
                "PRIMER_RIGHT_0_TM=61",
            ]
        )
        fake_spidey = "\n".join(
            [
                "--SPIDEY",
                "overall percent identity: 100.0%",
                "mRNA coverage: 100%",
                "Exon 1: 1-100 (mRNA)",
                "Exon 2: 101-200 (mRNA)",
            ]
        )
        with tempfile.TemporaryDirectory() as td:
            p3 = Path(td) / "primer3.out"
            mrna = Path(td) / "mrna.fasta"
            dna = Path(td) / "dna.fasta"
            p3.write_text(primer3_content, encoding="utf-8")
            mrna.write_text(">m\n" + ("ACGT" * 80) + "\n", encoding="utf-8")
            dna.write_text(">d\n" + ("ACGT" * 200) + "\n", encoding="utf-8")
            with patch("primerl.cli._run_spidey_alignment", return_value=(True, fake_spidey, "")):
                rc, payload = self._run(
                    [
                        "qpcr-design",
                        "--primer3-output",
                        str(p3),
                        "--template-len",
                        "300",
                        "--ie-span",
                        "--run-spidey",
                        "--spidey-path",
                        "spidey.exe",
                        "--mrna-fasta",
                        str(mrna),
                        "--genomic-fasta",
                        str(dna),
                    ]
                )
        self.assertEqual(rc, 0)
        self.assertEqual(payload["returned_pairs"], 1)
        self.assertEqual(payload["spidey"]["source"], "run_spidey")
        self.assertEqual(payload["spidey"]["source"], "run_spidey")

    def test_qpcr_design_run_spidey_mode_with_mock(self) -> None:
        primer3_content = "\n".join(
            [
                "PRIMER_LEFT_0=10,20",
                "PRIMER_RIGHT_0=180,20",
                "PRIMER_LEFT_0_SEQUENCE=AAAA",
                "PRIMER_RIGHT_0_SEQUENCE=TTTT",
                "PRIMER_LEFT_0_TM=60",
                "PRIMER_RIGHT_0_TM=61",
            ]
        )
        fake_spidey = "\n".join(
            [
                "spidey alignment report",
                "identity 100%",
                "coverage 100%",
                "Exon 1: 1-100 (mRNA)",
                "Exon 2: 101-200 (mRNA)",
            ]
        )
        with tempfile.TemporaryDirectory() as td:
            p3 = Path(td) / "primer3.out"
            mrna = Path(td) / "mrna.fasta"
            dna = Path(td) / "dna.fasta"
            p3.write_text(primer3_content, encoding="utf-8")
            mrna.write_text(">m\n" + ("ACGT" * 80) + "\n", encoding="utf-8")
            dna.write_text(">d\n" + ("ACGT" * 200) + "\n", encoding="utf-8")
            with patch("primerl.cli._run_spidey_alignment", return_value=(True, fake_spidey, "")):
                rc, payload = self._run(
                    [
                        "qpcr-design",
                        "--primer3-output",
                        str(p3),
                        "--template-len",
                        "300",
                        "--ie-span",
                        "--run-spidey",
                        "--spidey-path",
                        "spidey.exe",
                        "--mrna-fasta",
                        str(mrna),
                        "--genomic-fasta",
                        str(dna),
                    ]
                )
        self.assertEqual(rc, 0)
        self.assertEqual(payload["returned_pairs"], 1)
        self.assertEqual(payload["spidey"]["source"], "run_spidey")

    def test_ensembl_fetch_with_lookup_json(self) -> None:
        lookup = {
            "Transcript": [
                {"id": "ENST2", "display_name": "tx2", "length": 100},
                {"id": "ENST1", "display_name": "tx1", "length": 200},
            ]
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "lookup.json"
            p.write_text(json.dumps(lookup), encoding="utf-8")
            rc, payload = self._run(
                [
                    "ensembl-fetch",
                    "--species",
                    "Homo sapiens",
                    "--gene",
                    "ACTB",
                    "--seq-type",
                    "coding",
                    "--lookup-json",
                    str(p),
                ]
            )
        self.assertEqual(rc, 0)
        self.assertEqual(payload["mapped_seq_type"], "cds")
        self.assertEqual(payload["longest_transcript"]["transcript_id"], "ENST1")

    def test_perl_parity_from_json_files(self) -> None:
        perl_payload = {
            "stats": {"parsed": 5},
            "returned_pairs": 2,
            "pairs": [
                ["AAAA", 0, 20, "60", "TTTT", 0, 20, "60", 0, 100, "-1", 0, 0, "-1"],
                ["CCCC", 0, 20, "60", "GGGG", 0, 20, "60", 0, 101, "-1", 0, 0, "-1"],
            ],
        }
        python_payload = {
            "stats": {"parsed": 7},
            "returned_pairs": 2,
            "pairs": [
                ["CCCC", 0, 20, "60", "GGGG", 0, 20, "60", 0, 101, "-1", 0, 0, "-1"],
                ["AAAA", 0, 20, "60", "TTTT", 0, 20, "60", 0, 100, "-1", 0, 0, "-1"],
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            perl_p = Path(td) / "perl.json"
            py_p = Path(td) / "python.json"
            perl_p.write_text(json.dumps(perl_payload), encoding="utf-8")
            py_p.write_text(json.dumps(python_payload), encoding="utf-8")
            rc, payload = self._run(
                [
                    "perl-parity",
                    "--perl-json",
                    str(perl_p),
                    "--python-json",
                    str(py_p),
                    "--top-n",
                    "2",
                ]
            )
        self.assertEqual(rc, 0)
        self.assertEqual(payload["perl_parsed"], 5)
        self.assertEqual(payload["python_parsed"], 7)
        self.assertEqual(payload["overlap_count"], 2)

    def test_golden_write_and_check(self) -> None:
        current_payload = {
            "stats": {"parsed": 10, "skipped_order": 0, "skipped_span": 2, "skipped_overlap": 0},
            "returned_pairs": 50,
            "spidey": {
                "used": True,
                "source": "run_spidey",
                "spidey_signature": True,
                "full_identity_100": True,
                "full_coverage_100": True,
                "auto_boundary_count": 3,
                "manual_boundary_count": 0,
                "boundaries": [168, 261, 420],
            },
            "pairs": [],
        }
        with tempfile.TemporaryDirectory() as td:
            cur = Path(td) / "current.json"
            golden = Path(td) / "golden.json"
            cur.write_text(json.dumps(current_payload), encoding="utf-8")

            rc_write, _payload_write = self._run(
                [
                    "golden-write",
                    "--current-json",
                    str(cur),
                    "--output",
                    str(golden),
                ]
            )
            self.assertEqual(rc_write, 0)

            rc_check, payload_check = self._run(
                [
                    "golden-check",
                    "--current-json",
                    str(cur),
                    "--golden-json",
                    str(golden),
                ]
            )
        self.assertEqual(rc_check, 0)
        self.assertTrue(payload_check["pass"])


if __name__ == "__main__":
    unittest.main()


