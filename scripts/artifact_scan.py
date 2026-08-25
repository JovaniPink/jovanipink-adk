#!/usr/bin/env python3
"""Scan built Python archives before they can be treated as releasable."""

from __future__ import annotations

import re
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "absolute user path": re.compile(r"/(?:Users|home)/[^/\s]+/"),
}


def local_terms() -> tuple[str, ...]:
    path = ROOT / ".security-denylist"
    if not path.exists():
        return ()
    return tuple(
        line.strip().casefold()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def safe_path(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and not name.startswith("/")
        and ".." not in path.parts
        and "\\" not in name
    )


def zip_entries(path: Path) -> list[tuple[str, bytes, int]]:
    with zipfile.ZipFile(path) as archive:
        return [
            (item.filename, archive.read(item), item.external_attr >> 16)
            for item in archive.infolist()
            if not item.is_dir()
        ]


def tar_entries(path: Path) -> list[tuple[str, bytes, int]]:
    entries: list[tuple[str, bytes, int]] = []
    with tarfile.open(path, "r:gz") as archive:
        for item in archive.getmembers():
            if item.issym() or item.islnk():
                raise SystemExit(f"artifact contains a link: {item.name}")
            if not item.isfile():
                continue
            extracted = archive.extractfile(item)
            if extracted is None:
                raise SystemExit(f"artifact member cannot be read: {item.name}")
            entries.append((item.name, extracted.read(), item.mode))
    return entries


def project_identity() -> tuple[str, str]:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    raw_project = config.get("project")
    if not isinstance(raw_project, dict):
        raise SystemExit("pyproject.toml has no project table")
    project = cast(dict[str, object], raw_project)
    name = project.get("name")
    version = project.get("version")
    if not isinstance(name, str) or not isinstance(version, str):
        raise SystemExit("pyproject.toml project name and version must be strings")
    return name.replace("-", "_"), version


def expected_members(path: Path) -> set[str]:
    package_name, version = project_identity()
    source_root = ROOT / "src" / package_name
    source_files = {
        item.relative_to(ROOT).as_posix()
        for item in source_root.rglob("*.py")
        if item.is_file()
    }
    if not source_files:
        raise SystemExit(f"package source is missing: {source_root}")

    if path.suffix == ".whl":
        distribution = f"{package_name}-{version}.dist-info"
        return {
            *(item.removeprefix("src/") for item in source_files),
            f"{distribution}/METADATA",
            f"{distribution}/WHEEL",
            f"{distribution}/licenses/LICENSE",
            f"{distribution}/RECORD",
        }
    if path.name.endswith(".tar.gz"):
        root = f"{package_name}-{version}"
        return {
            *(f"{root}/{item}" for item in source_files),
            f"{root}/.gitignore",
            f"{root}/LICENSE",
            f"{root}/README.md",
            f"{root}/pyproject.toml",
            f"{root}/PKG-INFO",
        }
    raise SystemExit(f"unsupported artifact: {path}")


def validate_member_contract(path: Path, names: set[str]) -> None:
    expected = expected_members(path)
    unexpected = sorted(names - expected)
    missing = sorted(expected - names)
    if unexpected:
        raise SystemExit(
            f"artifact contains undeclared package members: {', '.join(unexpected)}"
        )
    if missing:
        raise SystemExit(
            f"artifact is missing required package members: {', '.join(missing)}"
        )


def scan(path: Path) -> int:
    if path.suffix == ".whl":
        entries = zip_entries(path)
    elif path.name.endswith(".tar.gz"):
        entries = tar_entries(path)
    else:
        raise SystemExit(f"unsupported artifact: {path}")
    names = [name for name, _, _ in entries]
    if len(names) != len(set(names)):
        raise SystemExit(f"artifact contains duplicate paths: {path}")
    validate_member_contract(path, set(names))
    terms = local_terms()
    for name, payload, mode in entries:
        if not safe_path(name):
            raise SystemExit(f"artifact contains an unsafe path: {name}")
        if mode & 0o111:
            raise SystemExit(f"artifact contains an executable file: {name}")
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as error:
            raise SystemExit(f"artifact contains non-text content: {name}") from error
        if any(byte > 127 for byte in payload):
            raise SystemExit(f"artifact contains non-ASCII content: {name}")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                raise SystemExit(f"artifact contains {label}: {name}")
        folded = text.casefold()
        if any(term in folded for term in terms):
            raise SystemExit(f"artifact contains a local denied term: {name}")
    print(f"artifact scan passed for {path.name} with {len(entries)} files")
    return len(entries)


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: artifact_scan.py ARTIFACT...")
    for argument in sys.argv[1:]:
        scan(Path(argument))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
