from __future__ import annotations

import io
import json
import unittest
import zipfile
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

from jovanipink_adk import build_synthetic_bundle


ROOT = Path(__file__).resolve().parents[1]


class JsonSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest_schema = json.loads(
            (ROOT / "schemas/bundle-manifest.schema.json").read_text(encoding="utf-8")
        )
        self.release_schema = json.loads(
            (ROOT / "schemas/release-receipt.schema.json").read_text(encoding="utf-8")
        )
        with zipfile.ZipFile(io.BytesIO(build_synthetic_bundle())) as archive:
            self.manifest = json.loads(archive.read("manifest.json"))
            self.release = json.loads(archive.read("release.json"))

    def test_schemas_are_valid_and_accept_the_synthetic_contract(self) -> None:
        Draft202012Validator.check_schema(self.manifest_schema)
        Draft202012Validator.check_schema(self.release_schema)
        Draft202012Validator(self.manifest_schema).validate(self.manifest)
        Draft202012Validator(self.release_schema).validate(self.release)

    def test_schemas_reject_unknown_fields(self) -> None:
        self.manifest["unexpected"] = True
        self.release["unexpected"] = True
        with self.assertRaises(ValidationError):
            Draft202012Validator(self.manifest_schema).validate(self.manifest)
        with self.assertRaises(ValidationError):
            Draft202012Validator(self.release_schema).validate(self.release)


if __name__ == "__main__":
    unittest.main()
