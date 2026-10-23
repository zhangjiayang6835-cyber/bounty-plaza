import os
import unittest
from unittest.mock import patch
from shell_driver_sh import (
    ShellType,
    ShellDriverBase,
    ShellDriverBash,
    ShellDriverZsh,
    ShellDriverSh,
    get_shell_driver,
)


class TestShellDriverSh(unittest.TestCase):
    def test_get_type(self):
        driver = ShellDriverSh(
            shell_abs_path="/bin/sh",
            shell_env_vars={},
            cache_dir_abs_path="/fake/cache",
        )
        self.assertEqual(driver.get_type(), ShellType.shell_sh)

    def test_get_init_file_basename(self):
        driver = ShellDriverSh(
            shell_abs_path="/bin/sh",
            shell_env_vars={},
            cache_dir_abs_path="/fake/cache",
        )
        self.assertEqual(driver.get_init_file_basename(), ".shrc")

    def test_get_source_builtin(self):
        driver = ShellDriverSh(
            shell_abs_path="/bin/sh",
            shell_env_vars={},
            cache_dir_abs_path="/fake/cache",
        )
        # POSIX `sh` uses `.` instead of `source`
        self.assertEqual(driver.get_source_builtin(), ".")

    def test_configure_interactive_shell_sets_ENV(self):
        driver = ShellDriverSh(
            shell_abs_path="/bin/sh",
            shell_env_vars={},
            cache_dir_abs_path="/fake/cache",
        )
        driver.configure_interactive_shell(False)
        self.assertEqual(driver.shell_env_vars, {"ENV": "/fake/cache/sh/.shrc"})
        self.assertEqual(driver.shell_args, ["/bin/sh"])

    def test_get_shell_driver_fallback_when_SHELL_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            driver = get_shell_driver("/fake/cache")
            self.assertIsInstance(driver, ShellDriverSh)
            self.assertEqual(driver.shell_abs_path, "/bin/sh")

    def test_get_shell_driver_when_SHELL_is_sh(self):
        with patch.dict(os.environ, {"SHELL": "/usr/bin/sh"}, clear=True):
            driver = get_shell_driver("/fake/cache")
            self.assertIsInstance(driver, ShellDriverSh)
            self.assertEqual(driver.shell_abs_path, "/usr/bin/sh")

    def test_get_shell_driver_when_SHELL_is_bash(self):
        with patch.dict(os.environ, {"SHELL": "/bin/bash"}, clear=True):
            driver = get_shell_driver("/fake/cache")
            self.assertIsInstance(driver, ShellDriverBash)
            self.assertEqual(driver.shell_abs_path, "/bin/bash")

    def test_get_shell_driver_when_SHELL_is_zsh(self):
        with patch.dict(os.environ, {"SHELL": "/usr/local/bin/zsh"}, clear=True):
            driver = get_shell_driver("/fake/cache")
            self.assertIsInstance(driver, ShellDriverZsh)
            self.assertEqual(driver.shell_abs_path, "/usr/local/bin/zsh")

    def test_get_shell_driver_unknown_shell_raises_ValueError(self):
        with patch.dict(os.environ, {"SHELL": "/usr/bin/fish"}, clear=True):
            with self.assertRaises(ValueError):
                get_shell_driver("/fake/cache")


if __name__ == "__main__":
    unittest.main()
