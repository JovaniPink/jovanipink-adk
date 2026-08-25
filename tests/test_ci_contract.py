from __future__ import annotations

import tomllib
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

    def test_bootstrap_and_static_checks_are_locked(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        requirements = (ROOT / "requirements-bootstrap-linux.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("--require-hashes --only-binary=:all:", workflow)
        self.assertIn("requirements-bootstrap-linux.txt", workflow)
        self.assertIn("uv run --frozen mypy src tests scripts", workflow)
        self.assertIn("uv run --frozen ruff check src tests scripts", workflow)
        self.assertIn("uv run --frozen ruff format --check src tests scripts", workflow)
        self.assertEqual(1, requirements.count("--hash=sha256:"))

    def test_license_scan_uses_cross_version_metadata_contract(self) -> None:
        source = (ROOT / "scripts/license_scan.py").read_text(encoding="utf-8")
        self.assertIn("PackageMetadata", source)
        self.assertIn("metadata_value", source)
        self.assertNotIn("metadata.get(", source)

    def test_source_distribution_has_a_minimal_source_selection(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        sdist = project["tool"]["hatch"]["build"]["targets"]["sdist"]
        included = set(sdist["include"])
        self.assertEqual(
            {"/src/jovanipink_adk", "/LICENSE", "/README.md", "/pyproject.toml"},
            included,
        )
        self.assertNotIn("evidence", str(included))
        self.assertNotIn("provenance", str(included))
        self.assertNotIn("tests", str(included))


if __name__ == "__main__":
    unittest.main()
