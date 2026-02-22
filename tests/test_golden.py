import unittest

from primerl.golden import compare_summary, extract_summary


class GoldenTests(unittest.TestCase):
    def test_extract_summary(self) -> None:
        payload = {
            "stats": {"parsed": 10, "skipped_order": 1, "skipped_span": 2, "skipped_overlap": 3},
            "returned_pairs": 50,
            "spidey": {"used": True, "source": "run_spidey", "boundaries": [1, 2]},
        }
        got = extract_summary(payload)
        self.assertEqual(got["stats.parsed"], 10)
        self.assertEqual(got["returned_pairs"], 50)
        self.assertEqual(got["spidey.boundaries"], [1, 2])

    def test_compare_summary(self) -> None:
        cur = {"a": 1, "b": 2}
        golden = {"a": 1, "b": 3}
        rep = compare_summary(cur, golden)
        self.assertFalse(rep["pass"])
        self.assertEqual(rep["diff_count"], 1)
        self.assertIn("b", rep["differences"])


if __name__ == "__main__":
    unittest.main()

