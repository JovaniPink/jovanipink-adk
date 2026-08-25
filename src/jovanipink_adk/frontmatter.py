"""A narrow standard-library parser for the accepted Agent Skill frontmatter."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import BundleVerificationError


SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOP_LEVEL_FIELDS = frozenset(
    {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
)


@dataclass(frozen=True)
class ParsedSkill:
    name: str
    description: str
    license: str | None
    compatibility: str | None
    metadata: dict[str, str]
    instructions: str


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_skill(text: str, expected_name: str) -> ParsedSkill:
    if not text.startswith("---\n"):
        raise BundleVerificationError("SKILL.md frontmatter is missing")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise BundleVerificationError("SKILL.md frontmatter is not closed")
    frontmatter = text[4:end]
    instructions = text[end + 5 :]
    values: dict[str, str] = {}
    metadata: dict[str, str] = {}
    in_metadata = False
    for line in frontmatter.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  "):
            if not in_metadata or ":" not in line:
                raise BundleVerificationError("unsupported nested skill frontmatter")
            key, value = line.strip().split(":", 1)
            if not key or not value.strip() or value.strip() in {"|", ">"}:
                raise BundleVerificationError("unsupported metadata value")
            metadata[key] = _unquote(value)
            continue
        in_metadata = False
        if ":" not in line:
            raise BundleVerificationError("invalid skill frontmatter line")
        key, value = line.split(":", 1)
        key = key.strip()
        if key not in TOP_LEVEL_FIELDS:
            raise BundleVerificationError(f"unknown skill frontmatter field: {key}")
        if key in values:
            raise BundleVerificationError(f"duplicate skill frontmatter field: {key}")
        if key == "allowed-tools":
            raise BundleVerificationError("allowed-tools is forbidden in runtime bundles")
        if key == "metadata":
            if value.strip() not in {"", "{}"}:
                raise BundleVerificationError("metadata must use simple nested string fields")
            values[key] = ""
            in_metadata = True
            continue
        if not value.strip() or value.strip() in {"|", ">"}:
            raise BundleVerificationError(f"skill frontmatter field {key} must be a scalar")
        values[key] = _unquote(value)
    name = values.get("name", "")
    description = values.get("description", "")
    if not SKILL_NAME.fullmatch(name) or len(name) > 64:
        raise BundleVerificationError(f"invalid skill name: {name or '[missing]'}")
    if name != expected_name:
        raise BundleVerificationError("skill name does not match its archive path")
    if not description or len(description) > 1024:
        raise BundleVerificationError("skill description must contain 1 to 1024 characters")
    if not instructions.strip():
        raise BundleVerificationError("skill instructions are empty")
    return ParsedSkill(
        name=name,
        description=description,
        license=values.get("license"),
        compatibility=values.get("compatibility"),
        metadata=metadata,
        instructions=instructions,
    )
