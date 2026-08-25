#!/usr/bin/env python3
"""Verify the locked dependency graph and immutable artifact hashes."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ADK = "2.7.1"
EXPECTED_ADK_WHEEL = (
    "sha256:cd21e37c9846a80086fd880924aa5548e625ef85178122b40cda81ef5316129f"
)
HASH = re.compile(r"^sha256:[0-9a-f]{64}$")


def main() -> int:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"]
    if dependencies != [f"google-adk=={EXPECTED_ADK}"]:
        raise SystemExit(
            "runtime dependencies must contain only the exact Google ADK pin"
        )

    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    packages = lock.get("package", [])
    if not isinstance(packages, list) or not packages:
        raise SystemExit("uv.lock contains no packages")

    adk = None
    for package in packages:
        name = package.get("name")
        source = package.get("source", {})
        if name == project["project"]["name"]:
            if source != {"editable": "."}:
                raise SystemExit(
                    "the local project must be the only editable dependency"
                )
            continue
        if source != {"registry": "https://pypi.org/simple"}:
            raise SystemExit(f"dependency {name} uses an unapproved source: {source}")
        artifacts = []
        if isinstance(package.get("sdist"), dict):
            artifacts.append(package["sdist"])
        artifacts.extend(package.get("wheels", []))
        if not artifacts:
            raise SystemExit(f"dependency {name} has no locked artifact")
        for artifact in artifacts:
            digest = artifact.get("hash", "")
            if not HASH.fullmatch(digest):
                raise SystemExit(f"dependency {name} has an invalid artifact hash")
        if name == "google-adk":
            adk = package

    if adk is None or adk.get("version") != EXPECTED_ADK:
        raise SystemExit(f"google-adk must be locked to {EXPECTED_ADK}")
    observed = {item.get("hash") for item in adk.get("wheels", [])}
    if EXPECTED_ADK_WHEEL not in observed:
        raise SystemExit("the reviewed google-adk wheel hash is missing from uv.lock")

    print(f"dependency review passed for {len(packages) - 1} locked packages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
