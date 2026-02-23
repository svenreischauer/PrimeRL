from pathlib import Path
import unittest

from primerl.mfeprimer_spec import (
    DEFAULT_SPEC_PARAM_TOKENS,
    SPEC_PRESET_SOFT,
    SPEC_PRESET_STRICT,
    SOFT_SPEC_PARAMS_RAW,
    STRICT_SPEC_PARAMS_RAW,
    build_mfeprimer_spec_cmd,
    preset_from_spec_param_raw,
    resolve_spec_param_tokens,
    spec_param_raw_for_preset,
)


class MfeprimerSpecParamTests(unittest.TestCase):
    def test_default_command_includes_paralog_sensitive_defaults(self) -> None:
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
        self.assertIn("-k", cmd)
        self.assertIn("--misMatch", cmd)
        self.assertEqual(cmd[cmd.index("-k") + 1], "9")
        self.assertEqual(cmd[cmd.index("--misMatch") + 1], "1")

    def test_custom_preference_overrides_defaults(self) -> None:
        custom_tokens = resolve_spec_param_tokens("-k 8 --misMatch 1")
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
        self.assertEqual(cmd[cmd.index("-k") + 1], "8")
        self.assertEqual(cmd[cmd.index("--misMatch") + 1], "1")
        self.assertNotEqual(cmd[cmd.index("-k") + 1], "9")

    def test_invalid_preference_falls_back_and_reports_warning(self) -> None:
        warnings: list[str] = []
        resolved = resolve_spec_param_tokens("spec -i hacked.fa --misMatch 3", on_error=warnings.append)
        self.assertEqual(resolved, DEFAULT_SPEC_PARAM_TOKENS)
        self.assertEqual(len(warnings), 1)
        self.assertIn("using defaults", warnings[0].lower())

    def test_preset_mapping_soft_and_strict(self) -> None:
        self.assertEqual(preset_from_spec_param_raw("-k 9 --misMatch 1"), SPEC_PRESET_SOFT)
        self.assertEqual(preset_from_spec_param_raw("-k 8 --misMatch 1"), SPEC_PRESET_STRICT)

    def test_spec_param_raw_for_preset(self) -> None:
        self.assertEqual(spec_param_raw_for_preset("Soft"), SOFT_SPEC_PARAMS_RAW)
        self.assertEqual(spec_param_raw_for_preset("Strict"), STRICT_SPEC_PARAMS_RAW)


if __name__ == "__main__":
    unittest.main()
