import unittest

from primerl.spidey_adapter import (
    SpideyRunResult,
    analyze_spidey_output,
    build_spidey_args,
    extract_intron_exon_bounds,
    run_spidey_with_transport,
)


class SpideyArgTests(unittest.TestCase):
    def test_build_args_basic(self) -> None:
        args = build_spidey_args(
            "Spidey.exe",
            "dna.tmp",
            "mrna.tmp",
            print_alignment=1,
            large_intron=False,
        )
        self.assertEqual(
            args,
            ["Spidey.exe", "-i", "dna.tmp", "-m", "mrna.tmp", "-p", "1"],
        )

    def test_build_args_large_intron(self) -> None:
        args = build_spidey_args(
            "Spidey.exe",
            "dna.tmp",
            "mrna.tmp",
            print_alignment=0,
            large_intron=True,
        )
        self.assertEqual(args[-1], "-X")

    def test_build_args_spidey_exec(self) -> None:
        args = build_spidey_args(
            "spidey.exe",
            "dna.tmp",
            "mrna.tmp",
            print_alignment=1,
            large_intron=True,
        )
        self.assertEqual(
            args,
            ["spidey.exe", "-i", "dna.tmp", "-m", "mrna.tmp", "-p", "1", "-X"],
        )


class SpideyTransportTests(unittest.TestCase):
    def test_run_success(self) -> None:
        def transport(_args: list[str]) -> tuple[int, str]:
            return 0, "--SPIDEY\noverall percent identity: 100.0%\nmRNA coverage: 100%"

        res = run_spidey_with_transport(["Spidey.exe"], transport)
        self.assertIsInstance(res, SpideyRunResult)
        self.assertTrue(res.ok)
        self.assertEqual(res.error, "")

    def test_run_failure(self) -> None:
        def transport(_args: list[str]) -> tuple[int, str]:
            return 1, "not found"

        res = run_spidey_with_transport(["Spidey.exe"], transport)
        self.assertFalse(res.ok)
        self.assertIn("exit code", res.error)


class SpideyOutputTests(unittest.TestCase):
    def test_analyze_output_ok(self) -> None:
        out = "--SPIDEY\noverall percent identity: 100.0%\nmRNA coverage: 100%"
        status = analyze_spidey_output(out)
        self.assertTrue(status.has_signature)
        self.assertTrue(status.full_identity)
        self.assertTrue(status.full_coverage)

    def test_analyze_output_partial(self) -> None:
        out = "--SPIDEY\noverall percent identity: 95.0%\nmRNA coverage: 80%"
        status = analyze_spidey_output(out)
        self.assertTrue(status.has_signature)
        self.assertFalse(status.full_identity)
        self.assertFalse(status.full_coverage)

    def test_analyze_output_spidey_signature(self) -> None:
        out = "spidey alignment report\nidentity 100%\ncoverage 100%"
        status = analyze_spidey_output(out)
        self.assertFalse(status.has_signature)
        self.assertFalse(status.full_identity)
        self.assertFalse(status.full_coverage)

    def test_extract_intron_exon_bounds(self) -> None:
        out = """
        Exon 1: 1-100 (mRNA)
        Exon 2: 101-220 (mRNA)
        Exon 3: 221-350 (mRNA)
        """
        # Perl keeps end coordinates then drops the last one.
        self.assertEqual(extract_intron_exon_bounds(out), [100, 220])

    def test_extract_bounds_empty(self) -> None:
        self.assertEqual(extract_intron_exon_bounds(""), [])

if __name__ == "__main__":
    unittest.main()
