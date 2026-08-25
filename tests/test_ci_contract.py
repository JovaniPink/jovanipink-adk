from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CiContractTests(unittest.TestCase):
    def test_evidence_directory_exists_before_audit_output(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        prepare = workflow.index("mkdir -p validation-artifacts")
        audit = workflow.index("--output validation-artifacts/dependency-audit.json")
        report = workflow.index("validation-artifacts/validation-report.json")
        self.assertLess(prepare, audit)
        self.assertLess(prepare, report)


if __name__ == "__main__":
    unittest.main()
