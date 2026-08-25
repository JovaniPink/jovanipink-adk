from __future__ import annotations

import io
import unittest
import warnings
import zipfile
from dataclasses import replace
from typing import cast

from jovanipink_adk import (
    BundleVerificationError,
    RuntimePolicy,
    build_synthetic_bundle,
    verify_skill_bundle,
)

from tests.support import rewrite_archive


class BundleVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = build_synthetic_bundle()
        self.policy = RuntimePolicy.for_testing({"fictional-support-policy"})

    def assert_rejected(
        self, payload: bytes, message: str, policy: RuntimePolicy | None = None
    ) -> None:
        with self.assertRaisesRegex(BundleVerificationError, message):
            verify_skill_bundle(payload, policy or self.policy)

    def test_valid_synthetic_bundle_verifies_read_only(self) -> None:
        verified = verify_skill_bundle(self.bundle, self.policy)
        self.assertEqual(("fictional-support-policy",), verified.skill_names)
        self.assertIn(
            "skills/fictional-support-policy/references/policy-facts.md", verified.files
        )
        with self.assertRaises(TypeError):
            cast(dict[str, bytes], verified.files)["new"] = b"no"

    def test_wrong_hash_and_undeclared_files_fail_closed(self) -> None:
        def wrong_hash(value: dict[str, object]) -> None:
            skills = value.get("skills")
            if (
                not isinstance(skills, list)
                or not skills
                or not isinstance(skills[0], dict)
            ):
                raise TypeError("synthetic manifest skills are malformed")
            files = skills[0].get("files")
            if (
                not isinstance(files, list)
                or not files
                or not isinstance(files[0], dict)
            ):
                raise TypeError("synthetic manifest files are malformed")
            files[0]["sha256"] = "0" * 64

        self.assert_rejected(
            rewrite_archive(self.bundle, transform_json={"manifest.json": wrong_hash}),
            "hash mismatch",
        )
        self.assert_rejected(
            rewrite_archive(
                self.bundle,
                append=[
                    ("skills/fictional-support-policy/references/extra.md", b"extra")
                ],
            ),
            "undeclared",
        )

    def test_release_state_and_version_policy_fail_closed(self) -> None:
        revoked = build_synthetic_bundle(lifecycle_state="revoked")
        self.assert_rejected(revoked, "revoked")
        stale = build_synthetic_bundle(
            valid_until="2020-01-01T00:00:00Z", lifecycle_state="released"
        )
        self.assert_rejected(stale, "expired")
        incompatible = build_synthetic_bundle(adk_version="0.0.1")
        self.assert_rejected(incompatible, "ADK version")
        production = replace(self.policy, runtime_mode="production")
        self.assert_rejected(self.bundle, "released", production)

    def test_archive_path_and_entry_attacks_fail_closed(self) -> None:
        attacks = (
            ("../escape.md", "path traversal"),
            ("/absolute.md", "absolute path"),
            (".hidden", "hidden"),
            (
                "skills/fictional-support-policy/scripts/run.py",
                "forbidden archive path",
            ),
            (
                "skills/fictional-support-policy/requirements.txt",
                "forbidden archive path",
            ),
            ("skills/FICTIONAL-support-policy/SKILL.md", "case-colliding"),
        )
        for name, message in attacks:
            with self.subTest(name=name):
                self.assert_rejected(
                    rewrite_archive(self.bundle, append=[(name, b"bad")]), message
                )

        symlink = zipfile.ZipInfo("skills/fictional-support-policy/references/link.md")
        symlink.create_system = 3
        symlink.external_attr = 0o120777 << 16
        self.assert_rejected(
            rewrite_archive(self.bundle, append=[(symlink, b"target")]), "symlink"
        )

        with zipfile.ZipFile(io.BytesIO(self.bundle)) as source:
            duplicate_content = source.read("release.json")
        self.assert_rejected(self._duplicate_release(duplicate_content), "duplicate")

    def _duplicate_release(self, content: bytes) -> bytes:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            return rewrite_archive(self.bundle, append=[("release.json", content)])

    def test_size_count_and_compression_limits_fail_closed(self) -> None:
        tiny_file_policy = replace(self.policy, maximum_file_size=32)
        self.assert_rejected(self.bundle, "file size", tiny_file_policy)
        tiny_count_policy = replace(self.policy, maximum_file_count=2)
        self.assert_rejected(self.bundle, "file count", tiny_count_policy)
        tiny_archive_policy = replace(
            self.policy, maximum_archive_size=len(self.bundle) - 1
        )
        self.assert_rejected(self.bundle, "archive size", tiny_archive_policy)
        compressed = rewrite_archive(
            self.bundle,
            append=[
                ("skills/fictional-support-policy/references/bomb.md", b"0" * 100_000)
            ],
        )
        strict_ratio = replace(self.policy, maximum_compression_ratio=5)
        self.assert_rejected(compressed, "compression ratio", strict_ratio)

    def test_policy_path_prefixes_and_extensions_are_enforced(self) -> None:
        wrong_prefix = replace(self.policy, allowed_path_prefixes=("private/",))
        self.assert_rejected(self.bundle, "runtime policy", wrong_prefix)
        wrong_extension = replace(self.policy, allowed_extensions=frozenset({".json"}))
        self.assert_rejected(self.bundle, "extension", wrong_extension)

    def test_invalid_text_frontmatter_and_skill_capabilities_fail_closed(self) -> None:
        invalid_utf8 = build_synthetic_bundle(reference_content=b"\xff\xfe")
        self.assert_rejected(invalid_utf8, "UTF-8")
        allowed_tools = build_synthetic_bundle(
            skill_content="""---
name: fictional-support-policy
description: Synthetic policy.
allowed-tools: dangerous-tool
---
Use the dangerous tool.
"""
        )
        self.assert_rejected(allowed_tools, "allowed-tools")
        wrong_name = build_synthetic_bundle(skill_name="Bad--Skill")
        self.assert_rejected(wrong_name, "skill name")
        invalid_frontmatter = build_synthetic_bundle(skill_content="No frontmatter")
        self.assert_rejected(invalid_frontmatter, "frontmatter")

    def test_manifest_unknown_fields_and_mutable_revisions_fail_closed(self) -> None:
        def add_unknown(value: dict[str, object]) -> None:
            value["unexpected"] = True

        def mutable(value: dict[str, object]) -> None:
            value["source_revision"] = "main"

        self.assert_rejected(
            rewrite_archive(self.bundle, transform_json={"manifest.json": add_unknown}),
            "unknown field",
        )
        self.assert_rejected(
            rewrite_archive(self.bundle, transform_json={"manifest.json": mutable}),
            "source revision",
        )

    def test_release_receipt_requires_exact_fields_and_release_evidence(self) -> None:
        def add_unknown(value: dict[str, object]) -> None:
            value["unexpected"] = True

        def release_without_evaluations(value: dict[str, object]) -> None:
            value["lifecycle_state"] = "released"
            value["evaluation_receipts"] = []
            value["approval_identity"] = "synthetic-approver"
            value["approved_at"] = "2026-08-25T00:00:00Z"

        def release_without_approval(value: dict[str, object]) -> None:
            value["lifecycle_state"] = "released"

        def release_without_attestation(value: dict[str, object]) -> None:
            value["lifecycle_state"] = "released"
            value["provenance_attestation_reference"] = ""
            value["approval_identity"] = "synthetic-approver"
            value["approved_at"] = "2026-08-25T00:00:00Z"

        self.assert_rejected(
            rewrite_archive(self.bundle, transform_json={"release.json": add_unknown}),
            "unknown field",
        )
        self.assert_rejected(
            rewrite_archive(
                self.bundle,
                transform_json={"release.json": release_without_evaluations},
            ),
            "evaluation evidence",
        )
        self.assert_rejected(
            rewrite_archive(
                self.bundle,
                transform_json={"release.json": release_without_approval},
            ),
            "approval evidence",
        )
        self.assert_rejected(
            rewrite_archive(
                self.bundle,
                transform_json={"release.json": release_without_attestation},
            ),
            "provenance attestation",
        )


if __name__ == "__main__":
    unittest.main()
