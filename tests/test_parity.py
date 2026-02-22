import json
import tempfile
import unittest
from pathlib import Path

from primerl.parity import compare_payloads, load_payload


class ParityTests(unittest.TestCase):
    def test_compare_payloads_overlap_and_rank_delta(self) -> None:
        perl_payload = {
            "stats": {"parsed": 10},
            "returned_pairs": 3,
            "pairs": [
                ["AAAA", 0, 20, "60", "TTTT", 0, 20, "60", 0, 100, "-1", 0, 0, "-1"],
                ["CCCC", 0, 20, "60", "GGGG", 0, 20, "60", 0, 101, "-1", 0, 0, "-1"],
                ["ACAC", 0, 20, "60", "GTGT", 0, 20, "60", 0, 102, "-1", 0, 0, "-1"],
            ],
        }
        python_payload = {
            "stats": {"parsed": 12},
            "returned_pairs": 3,
            "pairs": [
                ["CCCC", 0, 20, "60", "GGGG", 0, 20, "60", 0, 101, "-1", 0, 0, "-1"],
                ["AAAA", 0, 20, "60", "TTTT", 0, 20, "60", 0, 100, "-1", 0, 0, "-1"],
                ["TTAA", 0, 20, "60", "AATT", 0, 20, "60", 0, 103, "-1", 0, 0, "-1"],
            ],
        }
        got = compare_payloads(perl_payload, python_payload, top_n=3)
        self.assertEqual(got.perl_parsed, 10)
        self.assertEqual(got.python_parsed, 12)
        self.assertEqual(got.overlap_count, 2)
        self.assertEqual(got.only_perl_top_n, 1)
        self.assertEqual(got.only_python_top_n, 1)
        self.assertEqual(got.mean_rank_delta, 1.0)
        self.assertEqual(got.max_rank_delta, 1)

    def test_load_payload(self) -> None:
        payload = {"stats": {"parsed": 1}, "returned_pairs": 0, "pairs": []}
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            got = load_payload(str(p))
        self.assertEqual(got["stats"]["parsed"], 1)


if __name__ == "__main__":
    unittest.main()

