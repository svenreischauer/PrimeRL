import subprocess
import unittest
from unittest.mock import patch

from primerl import platform_compat


class PlatformCompatTests(unittest.TestCase):
    def test_candidate_exec_names_dedup(self) -> None:
        with patch.object(platform_compat, "BIN_EXT", ".exe"):
            self.assertEqual(platform_compat.candidate_exec_names("spidey"), ["spidey.exe", "spidey"])
            self.assertEqual(platform_compat.candidate_exec_names("tool.exe"), ["tool.exe", "tool"])
        with patch.object(platform_compat, "BIN_EXT", ""):
            self.assertEqual(platform_compat.candidate_exec_names("spidey"), ["spidey"])

    def test_normalize_exec_name(self) -> None:
        self.assertEqual(platform_compat.normalize_exec_name("C:/bin/Spidey.exe"), "spidey")
        self.assertEqual(platform_compat.normalize_exec_name("/usr/local/bin/minimap2"), "minimap2")

    def test_subprocess_run_windows_adds_no_window_flag(self) -> None:
        captured: dict[str, object] = {}

        def fake_run(*_args: object, **kwargs: object):
            captured.update(kwargs)
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        with patch.object(platform_compat, "IS_WINDOWS", True):
            with patch("primerl.platform_compat.subprocess.run", side_effect=fake_run):
                platform_compat.subprocess_run(["echo", "hi"])
        self.assertIn("creationflags", captured)
        self.assertNotEqual(int(captured["creationflags"]), 0)

    def test_subprocess_run_non_windows_keeps_kwargs(self) -> None:
        captured: dict[str, object] = {}

        def fake_run(*_args: object, **kwargs: object):
            captured.update(kwargs)
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        with patch.object(platform_compat, "IS_WINDOWS", False):
            with patch("primerl.platform_compat.subprocess.run", side_effect=fake_run):
                platform_compat.subprocess_run(["echo", "hi"], check=False)
        self.assertNotIn("creationflags", captured)
        self.assertIn("check", captured)

    def test_open_file_windows(self) -> None:
        with patch.object(platform_compat, "IS_WINDOWS", True):
            with patch("primerl.platform_compat.os.startfile", create=True) as startfile:
                self.assertTrue(platform_compat.open_file("x.txt"))
                startfile.assert_called_once_with("x.txt")

    def test_open_file_macos(self) -> None:
        cp = subprocess.CompletedProcess(args=["open", "x.txt"], returncode=0, stdout="", stderr="")
        with patch.object(platform_compat, "IS_WINDOWS", False):
            with patch.object(platform_compat, "IS_MACOS", True):
                with patch("primerl.platform_compat.subprocess.run", return_value=cp) as run:
                    self.assertTrue(platform_compat.open_file("x.txt"))
                    run.assert_called_once()
                    self.assertEqual(run.call_args.args[0], ["open", "x.txt"])

    def test_open_file_linux(self) -> None:
        cp = subprocess.CompletedProcess(args=["xdg-open", "x.txt"], returncode=0, stdout="", stderr="")
        with patch.object(platform_compat, "IS_WINDOWS", False):
            with patch.object(platform_compat, "IS_MACOS", False):
                with patch("primerl.platform_compat.subprocess.run", return_value=cp) as run:
                    self.assertTrue(platform_compat.open_file("x.txt"))
                    run.assert_called_once()
                    self.assertEqual(run.call_args.args[0], ["xdg-open", "x.txt"])


if __name__ == "__main__":
    unittest.main()
