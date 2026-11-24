"""
Semantic versioning utilities and validation for Skills.
"""

from __future__ import annotations

import re
from typing import Tuple

SEMVER_REGEX = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def is_valid_semver(version: str) -> bool:
    """Validates whether a string adheres to Semantic Versioning 2.0.0."""
    if not isinstance(version, str):
        return False
    return bool(SEMVER_REGEX.match(version.strip()))


def parse_semver(version: str) -> Tuple[int, int, int]:
    """Extracts (major, minor, patch) integers from a semver string."""
    match = SEMVER_REGEX.match(version.strip())
    if not match:
        raise ValueError(f"Invalid semver string: '{version}'")
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    return major, minor, patch


def compare_semver(v1: str, v2: str) -> int:
    """
    Compares two semantic version strings.
    Returns:
       1 if v1 > v2
      -1 if v1 < v2
       0 if v1 == v2
    """
    p1 = parse_semver(v1)
    p2 = parse_semver(v2)
    if p1 > p2:
        return 1
    if p1 < p2:
        return -1
    return 0


def bump_semver(version: str, bump_type: str = "patch") -> str:
    """Bumps a semver string by major, minor, or patch."""
    major, minor, patch = parse_semver(version)
    bump = bump_type.lower().strip()
    if bump == "major":
        return f"{major + 1}.0.0"
    elif bump == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Unknown bump type: '{bump_type}'. Choose major, minor, or patch.")
