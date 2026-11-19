"""SemVer parsing and range matching using only the standard library."""
import re

SEMVER_RE = re.compile(
    r"^(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?$"
)
PARTIAL_RE = re.compile(
    r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?$"
)

ZERO = 0
ONE = 1
WILDCARDS = frozenset({"*", "x", "X", "latest", ""})
OPERATORS = (">=", "<=", ">", "<", "=")


def parse_semver(version: str) -> tuple[int, int, int] | None:
    """Parse a full semantic version string into an integer triple."""
    match = SEMVER_RE.match(version.strip())
    if not match:
        return None
    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
    )


def is_prerelease(version: str) -> bool:
    """Check whether a version string contains a prerelease suffix."""
    return "-" in version


def parse_partial(text: str) -> tuple[int, int, int] | None:
    """Parse a partial or full numeric version into a triple."""
    cleaned = text.strip().lstrip("v")
    match = PARTIAL_RE.match(cleaned)
    if not match:
        return None

    major = int(match.group(1))
    minor = int(match.group(2)) if match.group(2) else ZERO
    patch = int(match.group(3)) if match.group(3) else ZERO

    return (major, minor, patch)


def _match_caret(
    candidate: tuple[int, int, int],
    base: tuple[int, int, int],
) -> bool:
    """Check caret range (^x.y.z) compatibility."""
    major, minor, patch = base

    if major != ZERO:
        upper = (major + ONE, ZERO, ZERO)
    elif minor != ZERO:
        upper = (ZERO, minor + ONE, ZERO)
    else:
        upper = (ZERO, ZERO, patch + ONE)

    return base <= candidate < upper


def _match_tilde(
    candidate: tuple[int, int, int],
    base: tuple[int, int, int],
) -> bool:
    """Check tilde range (~x.y.z) compatibility."""
    major, minor, _ = base
    upper = (major, minor + ONE, ZERO)

    return base <= candidate < upper


def _match_operator(
    candidate: tuple[int, int, int],
    operator: str,
    target: tuple[int, int, int],
) -> bool:
    """Compare candidate against target using a relational operator."""
    comparisons = {
        ">=": candidate >= target,
        "<=": candidate <= target,
        ">": candidate > target,
        "<": candidate < target,
        "=": candidate == target,
    }
    return comparisons[operator]


def _match_wildcard(
    candidate: tuple[int, int, int],
    token: str,
) -> bool:
    """Match wildcard expressions such as 1.x or 1.2.x."""
    parts = token.lower().split(".")

    for cand_part, pat_part in zip(candidate, parts):
        if pat_part in WILDCARDS:
            return True
        if not pat_part.isdigit():
            return False
        if cand_part != int(pat_part):
            return False

    return True


def _match_caret_token(
    candidate: tuple[int, int, int],
    token: str,
) -> bool:
    """Match a caret range token."""
    base = parse_partial(token[ONE:])
    return base is not None and _match_caret(candidate, base)


def _match_tilde_token(
    candidate: tuple[int, int, int],
    token: str,
) -> bool:
    """Match a tilde range token."""
    base = parse_partial(token[ONE:])
    return base is not None and _match_tilde(candidate, base)


def _match_operator_token(
    candidate: tuple[int, int, int],
    token: str,
) -> bool | None:
    """Match a token with a relational operator."""
    for op in OPERATORS:
        if token.startswith(op):
            target = parse_partial(token[len(op):])
            return (
                target is not None
                and _match_operator(candidate, op, target)
            )

    return None


def _match_token(
    candidate: tuple[int, int, int],
    token: str,
) -> bool:
    """Match a single comparator token against a SemVer triple."""
    if token in WILDCARDS:
        return True

    if token.startswith("^"):
        return _match_caret_token(candidate, token)

    if token.startswith("~"):
        return _match_tilde_token(candidate, token)
    operator_result = _match_operator_token(candidate, token)
    if operator_result is not None:
        return operator_result

    if "x" in token.lower() or "*" in token:
        return _match_wildcard(candidate, token)

    exact = parse_partial(token)
    return exact is not None and candidate == exact


def _match_branch(
    candidate: tuple[int, int, int],
    branch: str,
) -> bool:
    """Match one OR-branch of a version range."""
    tokens = branch.split()

    if not tokens:
        return True

    return all(_match_token(candidate, tok) for tok in tokens)


def matches_range(version: str, version_range: str) -> bool:
    """Return True if a version satisfies an npm version range."""
    candidate = parse_semver(version)

    if candidate is None:
        return False

    branches = [part.strip() for part in version_range.split("||")]
    return any(
        _match_branch(candidate, branch)
        for branch in branches
    )


def _select_highest(
    available: list[str],
    version_range: str,
    include_prerelease: bool,
) -> str | None:
    """Select the highest version matching the range."""
    matches = []

    for ver in available:
        if not include_prerelease and is_prerelease(ver):
            continue

        if matches_range(ver, version_range):
            parsed = parse_semver(ver)

            if parsed is not None:
                matches.append((parsed, ver))

    if not matches:
        return None

    matches.sort(key=lambda item: item[ZERO], reverse=True)
    return matches[ZERO][ONE]


def resolve_version(available: list[str], version_range: str) -> str:
    """Select the highest available version matching the SemVer range."""
    cleaned = version_range.strip()

    if cleaned in available:
        return cleaned

    stable = _select_highest(
        available,
        cleaned,
        include_prerelease=False,
    )
    if stable is not None:
        return stable

    any_version = _select_highest(
        available,
        cleaned,
        include_prerelease=True,
    )
    if any_version is not None:
        return any_version

    raise ValueError(
        f"No matching version found for range '{version_range}'."
    )