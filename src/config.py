"""Configuration loading and validation from INI files."""

import configparser
from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlparse

SECTION_NAME = "settings"
REQUIRED_KEYS = (
    "package_name",
    "repository_url",
    "test_mode",
    "package_version",
)
TRUE_VALUES = frozenset({"true", "yes", "1"})
FALSE_VALUES = frozenset({"false", "no", "0"})
ALLOWED_SCHEMES = frozenset({"http", "https"})
TEST_PKG_RE = re.compile(r"^[A-Z]+$")
NPM_PKG_RE = re.compile(
    r"^(@[a-z0-9-~][a-z0-9-._~]*/)?[a-z0-9-~][a-z0-9-._~]*$"
)
VERSION_RE = re.compile(r"^[0-9A-Za-z._+-]+$")


class ConfigError(ValueError):
    """Raised when configuration file or parameter values are invalid."""


@dataclass(frozen=True)
class AppConfig:
    """Validated application configuration parameters."""

    package_name: str
    repository_url: str
    test_mode: bool
    package_version: str
    reverse_mode: bool = False


def parse_bool(raw_value: str, param_name: str) -> bool:
    """Parse strict boolean string value from INI configuration."""
    normalized = raw_value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ConfigError(
        f"Invalid boolean for '{param_name}': '{raw_value}'."
    )


def validate_package_name(name: str, test_mode: bool) -> str:
    """Validate package name against test or npm naming conventions."""
    cleaned = name.strip()
    if not cleaned:
        raise ConfigError("Parameter 'package_name' cannot be empty.")
    pattern = TEST_PKG_RE if test_mode else NPM_PKG_RE
    if not pattern.match(cleaned):
        mode_desc = "uppercase Latin letters" if test_mode else "npm format"
        raise ConfigError(
            f"Invalid 'package_name' '{cleaned}' (expected {mode_desc})."
        )
    return cleaned


def validate_repository(repo_value: str, test_mode: bool) -> str:
    """Validate repository URL or local test repository file path."""
    cleaned = repo_value.strip()
    if not cleaned:
        raise ConfigError("Parameter 'repository_url' cannot be empty.")
    if test_mode:
        repo_path = Path(cleaned)
        if not repo_path.is_file():
            raise ConfigError(
                f"Test repository file not found: '{cleaned}'."
            )
        return cleaned
    parsed = urlparse(cleaned)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.netloc:
        raise ConfigError(
            f"Invalid repository URL: '{cleaned}'."
        )
    return cleaned.rstrip("/")


def validate_version(version: str) -> str:
    """Validate package version string."""
    cleaned = version.strip()
    if not cleaned:
        raise ConfigError("Parameter 'package_version' cannot be empty.")
    if not VERSION_RE.match(cleaned):
        raise ConfigError(f"Invalid 'package_version': '{cleaned}'.")
    return cleaned


def _read_ini_section(path: Path) -> configparser.SectionProxy:
    """Read and return the main settings section from an INI file."""
    if not path.is_file():
        raise ConfigError(f"Configuration file not found: '{path}'.")
    parser = configparser.ConfigParser()
    try:
        parser.read(path, encoding="utf-8")
    except configparser.Error as err:
        raise ConfigError(f"Failed to parse INI file: {err}") from err
    if SECTION_NAME not in parser:
        raise ConfigError(
            f"Missing required section '[{SECTION_NAME}]'."
        )
    section = parser[SECTION_NAME]
    for key in REQUIRED_KEYS:
        if key not in section:
            raise ConfigError(f"Missing required parameter: '{key}'.")
    return section


def load_config(config_path: str) -> AppConfig:
    """Load and validate application configuration from an INI file."""
    section = _read_ini_section(Path(config_path))
    test_mode = parse_bool(section["test_mode"], "test_mode")
    reverse_raw = section.get("reverse_mode", "false")
    reverse_mode = parse_bool(reverse_raw, "reverse_mode")
    package_name = validate_package_name(
        section["package_name"],
        test_mode,
    )
    repository_url = validate_repository(
        section["repository_url"],
        test_mode,
    )
    package_version = validate_version(section["package_version"])
    return AppConfig(
        package_name=package_name,
        repository_url=repository_url,
        test_mode=test_mode,
        package_version=package_version,
        reverse_mode=reverse_mode,
    )


def format_config(config: AppConfig) -> str:
    """Format configuration parameters as key=value lines."""
    lines = [
        f"package_name={config.package_name}",
        f"repository_url={config.repository_url}",
        f"test_mode={str(config.test_mode).lower()}",
        f"package_version={config.package_version}",
        f"reverse_mode={str(config.reverse_mode).lower()}",
    ]
    return "\n".join(lines)