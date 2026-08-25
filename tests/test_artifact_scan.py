from __future__ import annotations

import unittest
from pathlib import Path

from scripts.artifact_scan import expected_members, validate_member_contract


class ArtifactScanTests(unittest.TestCase):
    def test_expected_source_distribution_members_pass(self) -> None:
        path = Path("jovanipink_adk-0.1.0.tar.gz")
        validate_member_contract(path, expected_members(path))

    def test_repository_evidence_in_source_distribution_fails(self) -> None:
        path = Path("jovanipink_adk-0.1.0.tar.gz")
        members = expected_members(path) | {
            "jovanipink_adk-0.1.0/evidence/type-security-audit.json"
        }
        with self.assertRaisesRegex(SystemExit, "undeclared package members"):
            validate_member_contract(path, members)


if __name__ == "__main__":
    unittest.main()
