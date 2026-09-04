#!/usr/bin/env python3
"""Run the deterministic local acceptance suite."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_LINK = re.compile(r"\[[^]]+\]\((?!https?://)([^)#]+)(?:#[^)]+)?\)")
SCOPED_GUIDANCE_DIRECTORIES = ("schemas", "src", "tests", "scripts")
EXACT_CLAUDE_IMPORT = "@AGENTS.md\n"


def run(*arguments: str) -> None:
    subprocess.run([sys.executable, *arguments], cwd=ROOT, check=True)


def validate_json_files() -> None:
    paths = (
        sorted((ROOT / "schemas").glob("*.json"))
        + sorted((ROOT / "provenance").glob("*.json"))
        + sorted((ROOT / "evidence").glob("*.json"))
    )
    if not paths:
        raise SystemExit("schema and provenance records are required")
    for path in paths:
        json.loads(path.read_text(encoding="utf-8"))


def validate_local_links() -> None:
    for path in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
        for target in LOCAL_LINK.findall(path.read_text(encoding="utf-8")):
            resolved = (path.parent / target).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                raise SystemExit(
                    f"broken local link in {path.relative_to(ROOT)}: {target}"
                )


def validate_scoped_guidance() -> None:
    for directory in SCOPED_GUIDANCE_DIRECTORIES:
        scoped_root = ROOT / directory
        agents = scoped_root / "AGENTS.md"
        claude = scoped_root / "CLAUDE.md"
        if not agents.is_file():
            raise SystemExit(f"missing scoped guidance: {agents.relative_to(ROOT)}")
        if not claude.is_file():
            raise SystemExit(f"missing scoped Claude import: {claude.relative_to(ROOT)}")
        if claude.read_text(encoding="utf-8") != EXACT_CLAUDE_IMPORT:
            raise SystemExit(f"invalid scoped Claude import: {claude.relative_to(ROOT)}")


def main() -> int:
    validate_json_files()
    validate_local_links()
    validate_scoped_guidance()
    run("scripts/dependency_review.py")
    run("scripts/license_scan.py")
    run("scripts/security_scan.py")
    run("-m", "mypy", "src", "tests", "scripts")
    run("-m", "ruff", "check", "src", "tests", "scripts")
    run("-m", "compileall", "-q", "src", "tests", "scripts")
    run("-m", "unittest", "discover", "-s", "tests", "-v")
    print("validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
