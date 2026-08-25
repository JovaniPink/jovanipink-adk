#!/usr/bin/env python3
"""Scan publishable repository content for boundary and secret violations."""

from __future__ import annotations

import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    ".pytest_cache",
    "validation-artifacts",
}
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "absolute user path": re.compile(r"/(?:Users|home)/[^/\s]+/"),
}
TEXT_SUFFIXES = {
    ".json",
    ".lock",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def iter_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.name != ".security-denylist"
        and not any(part in EXCLUDED_PARTS for part in path.parts)
    )


def load_local_terms() -> tuple[str, ...]:
    path = ROOT / ".security-denylist"
    if not path.exists():
        return ()
    return tuple(
        line.strip().casefold()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def main() -> int:
    violations: list[str] = []
    local_terms = load_local_terms()
    for path in iter_files():
        relative = path.relative_to(ROOT).as_posix()
        if path.is_symlink():
            violations.append(f"symlink: {relative}")
            continue
        if path.stat().st_mode & 0o111:
            violations.append(f"executable file mode: {relative}")
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
            "LICENSE",
            ".gitignore",
        }:
            violations.append(f"unreviewed file type: {relative}")
            continue
        payload = path.read_bytes()
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            violations.append(f"invalid UTF-8: {relative}")
            continue
        if any(byte > 127 for byte in payload):
            violations.append(f"non-ASCII content: {relative}")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                violations.append(f"{label}: {relative}")
        folded = text.casefold()
        for term in local_terms:
            if term in folded:
                violations.append(f"local denied term: {relative}")
                break

    if violations:
        raise SystemExit("security scan failed:\n" + "\n".join(f"- {item}" for item in violations))
    print(f"security scan passed for {len(iter_files())} publishable files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
