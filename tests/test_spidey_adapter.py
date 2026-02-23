import unittest

from primerl.spidey_adapter import (
    SpideyRunResult,
    _convert_minimap2_sam_to_spidey,
    _is_minimap2,
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

    def test_build_args_minimap2_exec(self) -> None:
        args = build_spidey_args(
            "minimap2",
            "dna.tmp",
            "mrna.tmp",
            print_alignment=1,
            large_intron=True,
        )
        self.assertEqual(
            args,
            ["minimap2", "-x", "splice", "-a", "--secondary=no", "dna.tmp", "mrna.tmp"],
        )

    def test_is_minimap2(self) -> None:
        self.assertTrue(_is_minimap2("minimap2"))
        self.assertTrue(_is_minimap2("/usr/local/bin/minimap2"))
        self.assertFalse(_is_minimap2("spidey"))


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

    def test_run_success_minimap2_converts_to_spidey_like_output(self) -> None:
        sam = "\n".join(
            [
                "@HD\tVN:1.6\tSO:unsorted",
                "r_sec\t256\tchr1\t1\t60\t5M\t*\t0\t0\t*\t*",
                "r_sup\t2048\tchr1\t1\t60\t5M\t*\t0\t0\t*\t*",
                "r_pri\t0\tchr1\t1\t60\t10M5N20M3N15M\t*\t0\t0\t*\t*",
                "r_pri2\t0\tchr1\t1\t60\t5M5N5M\t*\t0\t0\t*\t*",
            ]
        )

        def transport(_args: list[str]) -> tuple[int, str]:
            return 0, sam

        res = run_spidey_with_transport(["minimap2"], transport)
        self.assertTrue(res.ok)
        self.assertIn("Exon 1: 1-10 (mRNA)", res.output)
        self.assertIn("Exon 2: 11-30 (mRNA)", res.output)
        self.assertIn("Exon 3: 31-45 (mRNA)", res.output)
        self.assertNotIn("5M5N5M", res.output)
        self.assertEqual(extract_intron_exon_bounds(res.output), [10, 30])


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

    def test_convert_minimap2_sam_to_spidey_text(self) -> None:
        sam = "read\t0\tchr1\t1\t60\t100M100N120M130N130M\t*\t0\t0\t*\t*"
        converted = _convert_minimap2_sam_to_spidey(sam)
        self.assertIn("Exon 1: 1-100 (mRNA)", converted)
        self.assertIn("Exon 2: 101-220 (mRNA)", converted)
        self.assertIn("Exon 3: 221-350 (mRNA)", converted)


if __name__ == "__main__":
    unittest.main()

