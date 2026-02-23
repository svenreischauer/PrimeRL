import unittest

from primerl.primer3_qpcr import (
    Primer3RunSettings,
    PrimerPair,
    QpcrFilterSettings,
    build_qpcr_input_text,
    collect_qpcr_pairs_from_primer3,
    parse_primer3_kv_output,
    run_primer3_qpcr_output,
    sort_qpcr_pairs,
)


def _pd_stub(s1: str, s2: str, full: bool) -> float:
    if full:
        table = {
            ("AAAA", "AAAA"): -7.0,
            ("AAAA", "TTTT"): -6.5,
            ("TTTT", "TTTT"): -8.0,
        }
    else:
        table = {
            ("AAAA", "AAAA"): -3.0,
            ("AAAA", "TTTT"): -5.0,
            ("TTTT", "TTTT"): -4.0,
        }
    return table.get((s1, s2), table.get((s2, s1), -1.0))


class ParsePrimer3Tests(unittest.TestCase):
    def test_parse_key_value_output(self) -> None:
        text = "\n".join([
            "PRIMER_LEFT_0=10,20",
            "PRIMER_RIGHT_0=80,20",
            "PRIMER_LEFT_0_SEQUENCE=AAAA",
            "PRIMER_RIGHT_0_SEQUENCE=TTTT",
            "",
        ])
        parsed = parse_primer3_kv_output(text)
        self.assertEqual(parsed["PRIMER_LEFT_0"], "10,20")
        self.assertEqual(parsed["PRIMER_RIGHT_0_SEQUENCE"], "TTTT")

    def test_build_qpcr_input_text(self) -> None:
        txt = build_qpcr_input_text("acgtNN", Primer3RunSettings())
        self.assertIn("SEQUENCE_TEMPLATE=acgt", txt)
        self.assertIn("PRIMER_NUM_RETURN=10000", txt)
        self.assertIn("PRIMER_MIN_TM=58.0", txt)


class RunPrimer3Tests(unittest.TestCase):
    def test_run_primer3_ok(self) -> None:
        def runner(_path: str, input_text: str) -> tuple[int, str, str]:
            self.assertIn("SEQUENCE_TEMPLATE=ACGT", input_text)
            return 0, "PRIMER_LEFT_0=10,20\nPRIMER_RIGHT_0=80,20\n", ""

        ok, out, err = run_primer3_qpcr_output("ACGT", "primer3_core.exe", Primer3RunSettings(), runner=runner)
        self.assertTrue(ok)
        self.assertIn("PRIMER_LEFT_0", out)
        self.assertEqual(err, "")

    def test_run_primer3_fail(self) -> None:
        def runner(_path: str, _input_text: str) -> tuple[int, str, str]:
            return 1, "", "boom"

        ok, out, err = run_primer3_qpcr_output("ACGT", "primer3_core.exe", Primer3RunSettings(), runner=runner)
        self.assertFalse(ok)
        self.assertEqual(out, "")
        self.assertIn("boom", err)

    def test_run_primer3_illegal_instruction(self) -> None:
        def runner(_path: str, _input_text: str) -> tuple[int, str, str]:
            return 0xC000001D, "", ""

        ok, out, err = run_primer3_qpcr_output("ACGT", "primer3_core_tuned.exe", Primer3RunSettings(), runner=runner)
        self.assertFalse(ok)
        self.assertEqual(out, "")
        self.assertIn("CPU-specific optimizations", err)

    def test_run_primer3_missing_dll(self) -> None:
        def runner(_path: str, _input_text: str) -> tuple[int, str, str]:
            return 0xC0000135, "", ""

        ok, out, err = run_primer3_qpcr_output("ACGT", "primer3_core_tuned.exe", Primer3RunSettings(), runner=runner)
        self.assertFalse(ok)
        self.assertEqual(out, "")
        self.assertIn("runtime libraries", err)

    def test_run_primer3_sigill_132(self) -> None:
        def runner(_path: str, _input_text: str) -> tuple[int, str, str]:
            return 132, "", ""

        ok, out, err = run_primer3_qpcr_output("ACGT", "primer3_core", Primer3RunSettings(), runner=runner)
        self.assertFalse(ok)
        self.assertEqual(out, "")
        self.assertIn("SIGILL", err)

    def test_run_primer3_macos_dyld_error(self) -> None:
        def runner(_path: str, _input_text: str) -> tuple[int, str, str]:
            return 1, "", "dyld: Library not loaded: libfoo.dylib"

        ok, out, err = run_primer3_qpcr_output("ACGT", "primer3_core", Primer3RunSettings(), runner=runner)
        self.assertFalse(ok)
        self.assertEqual(out, "")
        self.assertIn("macOS", err)


class CollectPrimer3Tests(unittest.TestCase):
    def test_collect_basic_pair(self) -> None:
        parsed = {
            "PRIMER_LEFT_0": "10,20",
            "PRIMER_RIGHT_0": "80,20",
            "PRIMER_LEFT_0_SEQUENCE": "AAAA",
            "PRIMER_RIGHT_0_SEQUENCE": "TTTT",
            "PRIMER_LEFT_0_TM": "60.123",
            "PRIMER_RIGHT_0_TM": "61.456",
            "PRIMER_PAIR_0_PRODUCT_SIZE": "70",
        }
        pairs, stats = collect_qpcr_pairs_from_primer3(
            parsed=parsed,
            template_len=100,
            settings=QpcrFilterSettings(),
            primer_dimer_fn=_pd_stub,
        )

        self.assertEqual(stats.parsed, 1)
        self.assertEqual(len(pairs), 1)

        p = pairs[0]
        self.assertEqual(p.seq_f, "AAAA")
        self.assertEqual(p.seq_r, "TTTT")
        self.assertEqual(p.pos_f, 10)
        self.assertEqual(p.pos_r, 19)
        self.assertEqual(p.tm_f, "60.12")
        self.assertEqual(p.tm_r, "61.46")
        self.assertEqual(p.pd_score, "-5.00")
        self.assertEqual(p.pd_score_full, "-8.00")

    def test_collect_uses_primer3_complementarity_when_present(self) -> None:
        parsed = {
            "PRIMER_LEFT_0": "10,20",
            "PRIMER_RIGHT_0": "80,20",
            "PRIMER_LEFT_0_SEQUENCE": "AAAA",
            "PRIMER_RIGHT_0_SEQUENCE": "TTTT",
            "PRIMER_LEFT_0_TM": "60",
            "PRIMER_RIGHT_0_TM": "61",
            "PRIMER_PAIR_0_COMPL_ANY_TH": "14.37",
            "PRIMER_PAIR_0_COMPL_END_TH": "6.40",
            "PRIMER_LEFT_0_SELF_ANY_TH": "3.10",
            "PRIMER_LEFT_0_SELF_END_TH": "2.00",
            "PRIMER_RIGHT_0_SELF_ANY_TH": "8.20",
            "PRIMER_RIGHT_0_SELF_END_TH": "1.10",
        }
        pairs, _stats = collect_qpcr_pairs_from_primer3(
            parsed=parsed,
            template_len=100,
            settings=QpcrFilterSettings(),
            primer_dimer_fn=_pd_stub,
        )
        self.assertEqual(len(pairs), 1)
        # Extensible score from END_TH set; full score from ANY_TH set.
        self.assertEqual(pairs[0].pd_score, "-6.40")
        self.assertEqual(pairs[0].pd_score_full, "-14.37")

    def test_skip_on_order(self) -> None:
        parsed = {
            "PRIMER_LEFT_0": "10,20",
            "PRIMER_RIGHT_0": "25,20",
            "PRIMER_LEFT_0_SEQUENCE": "AAAA",
            "PRIMER_RIGHT_0_SEQUENCE": "TTTT",
            "PRIMER_LEFT_0_TM": "60",
            "PRIMER_RIGHT_0_TM": "61",
        }
        pairs, stats = collect_qpcr_pairs_from_primer3(
            parsed=parsed,
            template_len=100,
            settings=QpcrFilterSettings(),
            primer_dimer_fn=_pd_stub,
        )
        self.assertEqual(len(pairs), 0)
        self.assertEqual(stats.skipped_order, 1)

    def test_skip_on_ie_span(self) -> None:
        parsed = {
            "PRIMER_LEFT_0": "10,20",
            "PRIMER_RIGHT_0": "80,20",
            "PRIMER_LEFT_0_SEQUENCE": "AAAA",
            "PRIMER_RIGHT_0_SEQUENCE": "TTTT",
            "PRIMER_LEFT_0_TM": "60",
            "PRIMER_RIGHT_0_TM": "61",
        }
        settings = QpcrFilterSettings(ie_span=True, intron_exon_bounds=(5,))
        pairs, stats = collect_qpcr_pairs_from_primer3(
            parsed=parsed,
            template_len=100,
            settings=settings,
            primer_dimer_fn=_pd_stub,
        )
        self.assertEqual(len(pairs), 0)
        self.assertEqual(stats.skipped_span, 1)

    def test_skip_on_ie_overlap(self) -> None:
        parsed = {
            "PRIMER_LEFT_0": "10,20",
            "PRIMER_RIGHT_0": "80,20",
            "PRIMER_LEFT_0_SEQUENCE": "AAAA",
            "PRIMER_RIGHT_0_SEQUENCE": "TTTT",
            "PRIMER_LEFT_0_TM": "60",
            "PRIMER_RIGHT_0_TM": "61",
        }
        settings = QpcrFilterSettings(
            ie_overlap=True,
            exclude_ie=2,
            intron_exon_bounds=(50,),
        )
        pairs, stats = collect_qpcr_pairs_from_primer3(
            parsed=parsed,
            template_len=100,
            settings=settings,
            primer_dimer_fn=_pd_stub,
        )
        self.assertEqual(len(pairs), 0)
        self.assertEqual(stats.skipped_overlap, 1)

    def test_exclude_runs_and_repeats(self) -> None:
        parsed = {
            "PRIMER_LEFT_0": "10,20",
            "PRIMER_RIGHT_0": "80,20",
            "PRIMER_LEFT_0_SEQUENCE": "AAAAA",
            "PRIMER_RIGHT_0_SEQUENCE": "TTTT",
            "PRIMER_LEFT_0_TM": "60",
            "PRIMER_RIGHT_0_TM": "61",
        }
        settings = QpcrFilterSettings(exclude_rr_q=True, run=4, repeat=4)
        pairs, stats = collect_qpcr_pairs_from_primer3(
            parsed=parsed,
            template_len=100,
            settings=settings,
            primer_dimer_fn=_pd_stub,
        )
        self.assertEqual(len(pairs), 0)
        self.assertEqual(stats.parsed, 1)


class SortPrimer3Tests(unittest.TestCase):
    def test_sort_perl_default(self) -> None:
        rows = [
            PrimerPair("A", 0, 20, "60.00", "T", 0, 20, "60.00", 100, 100, "-4.00", pd_score_full="-3.00"),
            PrimerPair("B", 0, 20, "60.00", "G", 0, 20, "60.00", 100, 100, "-2.00", pd_score_full="-8.00"),
            PrimerPair("C", 0, 20, "60.00", "C", 0, 20, "60.00", 100, 100, "-2.00", pd_score_full="-1.00"),
        ]
        sorted_rows = sort_qpcr_pairs(rows, sort_by="perl_default")
        # Highest pd_score first; ties resolved by highest full dimer score.
        self.assertEqual([r.seq_f for r in sorted_rows], ["C", "B", "A"])

    def test_sort_amp_size(self) -> None:
        rows = [
            PrimerPair("A", 0, 20, "60.00", "T", 0, 20, "60.00", 100, 300, "-1.00", pd_score_full="-1.00"),
            PrimerPair("B", 0, 20, "60.00", "G", 0, 20, "60.00", 100, 120, "-1.00", pd_score_full="-1.00"),
        ]
        sorted_rows = sort_qpcr_pairs(rows, sort_by="amp_size")
        self.assertEqual([r.seq_f for r in sorted_rows], ["B", "A"])


if __name__ == "__main__":
    unittest.main()
