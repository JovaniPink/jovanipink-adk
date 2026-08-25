#!/usr/bin/env python3
"""Write a small machine-readable record after validation succeeds."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: write_validation_report.py OUTPUT")
    destination = Path(sys.argv[1])
    destination.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": "1",
        "status": "pass",
        "source_revision": os.environ.get("GITHUB_SHA", "local-uncommitted"),
        "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "python_version": ".".join(str(item) for item in sys.version_info[:3]),
        "adk_version": importlib.metadata.version("google-adk"),
        "adapter_version": importlib.metadata.version("jovanipink-adk"),
        "uv_lock_sha256": sha256(ROOT / "uv.lock"),
        "provenance_sha256": {
            path.name: sha256(path) for path in sorted((ROOT / "provenance").glob("*.json"))
        },
    }
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
