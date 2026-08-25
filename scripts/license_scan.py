#!/usr/bin/env python3
"""Fail when an installed dependency lacks acceptable license evidence."""

from __future__ import annotations

from importlib.metadata import Distribution, distributions


DISALLOWED = ("AGPL", "GPL", "SSPL", "PROPRIETARY", "COMMERCIAL")
ACCEPTED = ("APACHE", "BSD", "ISC", "MIT", "MPL", "PSF")
IGNORED = {"jovanipink-adk", "pip"}


def evidence(distribution: Distribution) -> str:
    metadata = distribution.metadata
    values = [
        metadata.get("License-Expression") or "",
        metadata.get("License") or "",
    ]
    values.extend(
        item for item in metadata.get_all("Classifier") or [] if item.startswith("License ::")
    )
    return " | ".join(value for value in values if value).upper()


def main() -> int:
    reviewed = 0
    for distribution in sorted(
        distributions(), key=lambda item: (item.metadata.get("Name") or "").lower()
    ):
        name = distribution.metadata.get("Name") or "[unknown]"
        if name.lower() in IGNORED:
            continue
        observed = evidence(distribution)
        if not observed:
            raise SystemExit(f"dependency {name} has no installed license evidence")
        if any(term in observed for term in DISALLOWED):
            raise SystemExit(f"dependency {name} has a disallowed license signal: {observed}")
        if not any(term in observed for term in ACCEPTED):
            raise SystemExit(f"dependency {name} has an unreviewed license signal: {observed}")
        reviewed += 1
    print(f"license scan passed for {reviewed} installed dependencies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
