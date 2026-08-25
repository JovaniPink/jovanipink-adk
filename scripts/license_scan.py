#!/usr/bin/env python3
"""Fail when an installed dependency lacks acceptable license evidence."""

from __future__ import annotations

from importlib.metadata import Distribution, PackageMetadata, distributions


DISALLOWED = ("AGPL", "GPL", "SSPL", "PROPRIETARY", "COMMERCIAL")
ACCEPTED = ("APACHE", "BSD", "ISC", "MIT", "MPL", "PSF")
IGNORED = {"jovanipink-adk", "pip"}


def metadata_value(metadata: PackageMetadata, key: str) -> str:
    """Read one metadata field through the cross-version mapping contract."""

    values = metadata.get_all(key, [])
    return values[0] if values else ""


def evidence(distribution: Distribution) -> str:
    metadata = distribution.metadata
    values = [
        metadata_value(metadata, "License-Expression"),
        metadata_value(metadata, "License"),
    ]
    values.extend(
        item for item in metadata.get_all("Classifier") or [] if item.startswith("License ::")
    )
    return " | ".join(value for value in values if value).upper()


def main() -> int:
    reviewed = 0
    for distribution in sorted(
        distributions(), key=lambda item: metadata_value(item.metadata, "Name").lower()
    ):
        name = metadata_value(distribution.metadata, "Name") or "[unknown]"
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
