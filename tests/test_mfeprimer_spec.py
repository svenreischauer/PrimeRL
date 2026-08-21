import tempfile
import unittest
from pathlib import Path

from primerl.mfeprimer_spec import (
    DEFAULT_SPEC_PARAM_TOKENS,
    build_mfeprimer_spec_cmd,
    find_mfeprimer_binary_index,
    normalize_spec_param_raw,
    parse_spec_param_tokens,
    resolve_spec_param_tokens,
)


class MfeprimerSpecParamTests(unittest.TestCase):
    def test_default_command_lets_mfeprimer_detect_k_from_index(self) -> None:
        cmd = build_mfeprimer_spec_cmd(
            exe=Path("mfeprimer.exe"),
            inp=Path("pairs.tsv"),
            db=Path("db.fa"),
            out=Path("out.txt"),
            min_amp_size=80,
            max_amp_size=300,
            threads_per_job=4,
            spec_extra_args=None,
        )
        self.assertNotIn("-k", cmd)
        self.assertIn("--misMatch", cmd)
        self.assertEqual(cmd[cmd.index("--misMatch") + 1], "1")

    def test_custom_non_k_preference_overrides_defaults(self) -> None:
        custom_tokens = resolve_spec_param_tokens("--misMatch 2")
        cmd = build_mfeprimer_spec_cmd(
            exe=Path("mfeprimer.exe"),
            inp=Path("pairs.tsv"),
            db=Path("db.fa"),
            out=Path("out.txt"),
            min_amp_size=80,
            max_amp_size=300,
            threads_per_job=4,
            spec_extra_args=custom_tokens,
        )
        self.assertNotIn("-k", cmd)
        self.assertEqual(cmd[cmd.index("--misMatch") + 1], "2")

    def test_legacy_saved_k_is_removed_but_other_settings_are_retained(self) -> None:
        tokens, warning = parse_spec_param_tokens("-k 8 --misMatch 2")
        self.assertEqual(tokens, ["--misMatch", "2"])
        self.assertIsNotNone(warning)
        self.assertIn("auto-detected", str(warning))
        self.assertEqual(normalize_spec_param_raw("-k=9 --misMatch 1"), "--misMatch 1")

    def test_command_defensively_removes_query_k(self) -> None:
        cmd = build_mfeprimer_spec_cmd(
            exe=Path("mfeprimer.exe"),
            inp=Path("pairs.tsv"),
            db=Path("db.fa"),
            out=Path("out.txt"),
            min_amp_size=80,
            max_amp_size=300,
            threads_per_job=4,
            spec_extra_args=["-k", "8", "--misMatch", "1"],
        )
        self.assertNotIn("-k", cmd)
        self.assertEqual(cmd[cmd.index("--misMatch") + 1], "1")

    def test_invalid_preference_falls_back_and_reports_warning(self) -> None:
        warnings: list[str] = []
        resolved = resolve_spec_param_tokens("spec -i hacked.fa --misMatch 3", on_error=warnings.append)
        self.assertEqual(resolved, DEFAULT_SPEC_PARAM_TOKENS)
        self.assertEqual(len(warnings), 1)
        self.assertIn("using defaults", warnings[0].lower())

    def test_only_binary_index_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fasta = Path(temp_dir) / "transcriptome.fa"
            binary = Path(f"{fasta}.primerqc.bin")
            legacy = Path(f"{fasta}.primerqc")
            self.assertEqual(binary, Path(f"{fasta}.primerqc.bin"))
            self.assertIsNone(find_mfeprimer_binary_index(fasta))

            legacy.touch()
            self.assertIsNone(find_mfeprimer_binary_index(fasta))

            binary.touch()
            self.assertEqual(find_mfeprimer_binary_index(fasta), binary)


if __name__ == "__main__":
    unittest.main()
