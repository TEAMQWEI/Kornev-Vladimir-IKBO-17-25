"""Fetching dependency data from npm registries and test files."""

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from src.config import TEST_PKG_RE
from src.semver_util import resolve_version

DEFAULT_TIMEOUT = 15
USER_AGENT = "dep-graph-visualizer/1.0"
SEPARATOR = ":"
DEP_DELIMITER = ","
PAIR_PARTS = 2
KEY_INDEX = 0
VAL_INDEX = 1


class FetchError(RuntimeError):
    """Raised when dependency metadata cannot be fetched or parsed."""


class NpmRegistryFetcher:
    """HTTP client for querying npm registry metadata directly."""

    def __init__(
        self,
        registry_url: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize fetcher with base registry URL and request timeout."""
        self._registry_url = registry_url.rstrip("/")
        self._timeout = timeout
        self._cache: dict[str, dict] = {}

    def _build_package_url(self, package_name: str) -> str:
        """Build URL-encoded package metadata endpoint."""
        encoded = quote(package_name, safe="@")
        return f"{self._registry_url}/{encoded}"

    def fetch_metadata(self, package_name: str) -> dict:
        """Download and cache package JSON metadata from the registry."""
        if package_name in self._cache:
            return self._cache[package_name]
        url = self._build_package_url(package_name)
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=self._timeout) as response:
                raw_data = response.read().decode("utf-8")
        except HTTPError as err:
            raise FetchError(
                f"HTTP {err.code} fetching '{package_name}' from {url}."
            ) from err
        except URLError as err:
            raise FetchError(
                f"Network error fetching '{package_name}': {err.reason}."
            ) from err
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError as err:
            raise FetchError(
                f"Invalid JSON returned for '{package_name}'."
            ) from err
        self._cache[package_name] = data
        return data

    def get_direct_dependencies(
        self,
        package_name: str,
        version: str,
    ) -> dict[str, str]:
        """Return direct dependencies mapping for a specific version."""
        metadata = self.fetch_metadata(package_name)
        versions = metadata.get("versions", {})
        if version not in versions:
            raise FetchError(
                f"Version '{version}' not found for '{package_name}'."
            )
        version_data = versions[version]
        deps = version_data.get("dependencies")
        return dict(deps) if isinstance(deps, dict) else {}

    def resolve_dependency_version(
        self,
        package_name: str,
        version_range: str,
    ) -> str:
        """Resolve a SemVer range to a concrete version in the registry."""
        metadata = self.fetch_metadata(package_name)
        versions = list(metadata.get("versions", {}).keys())
        if not versions:
            raise FetchError(f"No versions available for '{package_name}'.")
        try:
            return resolve_version(versions, version_range)
        except ValueError as err:
            raise FetchError(
                f"Cannot resolve '{package_name}@{version_range}': {err}"
            ) from err


def _parse_test_line(line: str, line_num: int) -> tuple[str, list[str]]:
    """Parse one adjacency line of format 'A: B, C'."""
    parts = line.split(SEPARATOR)
    if len(parts) != PAIR_PARTS:
        raise FetchError(
            f"Invalid format at line {line_num}: '{line}'."
        )
    pkg = parts[KEY_INDEX].strip()
    if not TEST_PKG_RE.match(pkg):
        raise FetchError(
            f"Invalid test package name '{pkg}' at line {line_num}."
        )
    raw_deps = parts[VAL_INDEX].strip()
    if not raw_deps:
        return (pkg, [])
    deps = [item.strip() for item in raw_deps.split(DEP_DELIMITER)]
    for dep in deps:
        if not TEST_PKG_RE.match(dep):
            raise FetchError(
                f"Invalid dependency '{dep}' at line {line_num}."
            )
    return (pkg, deps)


def load_test_repository(file_path: str) -> dict[str, list[str]]:
    """Load a test dependency graph from a local text file."""
    path = Path(file_path)
    if not path.is_file():
        raise FetchError(f"Test repository file not found: '{file_path}'.")
    graph: dict[str, list[str]] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        pkg, deps = _parse_test_line(stripped, index)
        graph[pkg] = deps
    for deps in list(graph.values()):
        for dep in deps:
            graph.setdefault(dep, [])
    return graph