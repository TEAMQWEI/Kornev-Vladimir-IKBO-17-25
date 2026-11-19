"""Unit tests for SemVer matching and npm registry fetching."""

import io
import json
import unittest
from unittest.mock import patch

from src.fetcher import FetchError, NpmRegistryFetcher
from src.semver_util import matches_range, resolve_version


class TestSemverAndFetcher(unittest.TestCase):
    """Verify SemVer resolution and mocked npm registry requests."""

    def test_caret_and_tilde_matching(self) -> None:
        """Verify caret and tilde range semantics."""
        self.assertTrue(matches_range("4.3.0", "^4.1.0"))
        self.assertFalse(matches_range("5.0.0", "^4.1.0"))
        self.assertTrue(matches_range("0.2.5", "^0.2.3"))
        self.assertFalse(matches_range("0.3.0", "^0.2.3"))
        self.assertTrue(matches_range("1.2.9", "~1.2.3"))
        self.assertFalse(matches_range("1.3.0", "~1.2.3"))

    def test_resolve_highest_matching_version(self) -> None:
        """Pick highest stable version matching OR/comparator range."""
        versions = ["1.0.0", "1.4.2", "2.0.0-alpha.1", "2.1.0", "3.0.0"]
        self.assertEqual(resolve_version(versions, "^1.0.0"), "1.4.2")
        self.assertEqual(
            resolve_version(versions, ">=1.0.0 <3.0.0"),
            "2.1.0",
        )

    def test_fetch_direct_dependencies(self) -> None:
        """Extract direct dependencies from mocked registry JSON."""
        payload = {
            "versions": {
                "4.3.7": {
                    "dependencies": {"ms": "^2.1.3"}
                }
            }
        }
        mock_response = io.BytesIO(json.dumps(payload).encode("utf-8"))
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda *args: None
        fetcher = NpmRegistryFetcher("https://registry.npmjs.org")
        with patch("src.fetcher.urlopen", return_value=mock_response):
            deps = fetcher.get_direct_dependencies("debug", "4.3.7")
        self.assertEqual(deps, {"ms": "^2.1.3"})

    def test_missing_version_raises(self) -> None:
        """Raise FetchError when requested version is absent."""
        payload = {"versions": {"1.0.0": {}}}
        mock_response = io.BytesIO(json.dumps(payload).encode("utf-8"))
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda *args: None
        fetcher = NpmRegistryFetcher("https://registry.npmjs.org")
        with patch("src.fetcher.urlopen", return_value=mock_response):
            with self.assertRaises(FetchError):
                fetcher.get_direct_dependencies("demo", "9.9.9")


if __name__ == "__main__":
    unittest.main()