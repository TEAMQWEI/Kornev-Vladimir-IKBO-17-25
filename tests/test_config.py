"""Unit tests for INI configuration loading and validation."""

from pathlib import Path
import tempfile
import unittest

from src.config import ConfigError, format_config, load_config


class TestConfigValidation(unittest.TestCase):
    """Verify valid parsing and error handling for all parameters."""

    def _write_temp(self, content: str) -> str:
        """Create a temporary file with given text and return its path."""
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".ini",
            encoding="utf-8",
            delete=False,
        )
        tmp.write(content)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return tmp.name

    def test_valid_npm_config(self) -> None:
        """Load valid npm configuration and format key=value output."""
        path = self._write_temp(
            "[settings]\n"
            "package_name = chalk\n"
            "repository_url = https://registry.npmjs.org\n"
            "test_mode = false\n"
            "package_version = 4.1.2\n"
        )
        cfg = load_config(path)
        self.assertEqual(cfg.package_name, "chalk")
        self.assertFalse(cfg.test_mode)
        self.assertIn("package_name=chalk", format_config(cfg))

    def test_valid_test_mode_config(self) -> None:
        """Load valid configuration pointing to a local test file."""
        repo_path = self._write_temp("A: B\nB:\n")
        cfg_path = self._write_temp(
            "[settings]\n"
            "package_name = A\n"
            f"repository_url = {repo_path}\n"
            "test_mode = true\n"
            "package_version = 1.0.0\n"
        )
        cfg = load_config(cfg_path)
        self.assertTrue(cfg.test_mode)
        self.assertEqual(cfg.package_name, "A")

    def test_missing_file_raises(self) -> None:
        """Raise ConfigError if configuration file does not exist."""
        with self.assertRaises(ConfigError):
            load_config("/nonexistent/path/config.ini")

    def test_missing_section_raises(self) -> None:
        """Raise ConfigError when [settings] section is absent."""
        path = self._write_temp("[other]\npackage_name = A\n")
        with self.assertRaises(ConfigError):
            load_config(path)

    def test_invalid_boolean_raises(self) -> None:
        """Raise ConfigError on non-boolean test_mode value."""
        path = self._write_temp(
            "[settings]\n"
            "package_name = chalk\n"
            "repository_url = https://registry.npmjs.org\n"
            "test_mode = maybe\n"
            "package_version = 4.1.2\n"
        )
        with self.assertRaises(ConfigError):
            load_config(path)

    def test_invalid_url_raises(self) -> None:
        """Raise ConfigError when repository_url is not HTTP/HTTPS."""
        path = self._write_temp(
            "[settings]\n"
            "package_name = chalk\n"
            "repository_url = ftp://invalid-host\n"
            "test_mode = false\n"
            "package_version = 4.1.2\n"
        )
        with self.assertRaises(ConfigError):
            load_config(path)

    def test_invalid_test_package_name_raises(self) -> None:
        """Raise ConfigError if test_mode package is not uppercase."""
        repo_path = self._write_temp("A:\n")
        cfg_path = self._write_temp(
            "[settings]\n"
            "package_name = lower\n"
            f"repository_url = {repo_path}\n"
            "test_mode = true\n"
            "package_version = 1.0.0\n"
        )
        with self.assertRaises(ConfigError):
            load_config(cfg_path)

    def test_empty_version_raises(self) -> None:
        """Raise ConfigError when package_version is empty."""
        path = self._write_temp(
            "[settings]\n"
            "package_name = chalk\n"
            "repository_url = https://registry.npmjs.org\n"
            "test_mode = false\n"
            "package_version =\n"
        )
        with self.assertRaises(ConfigError):
            load_config(path)


if __name__ == "__main__":
    unittest.main()