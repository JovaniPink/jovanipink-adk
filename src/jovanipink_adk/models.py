"""Immutable public contracts for verified runtime bundles."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, Mapping


LifecycleState = Literal["reviewed", "evaluated", "released", "revoked"]
RuntimeMode = Literal["test", "production"]


@dataclass(frozen=True)
class SkillFile:
    path: str
    sha256: str


@dataclass(frozen=True)
class ManifestSkill:
    name: str
    path: str
    files: tuple[SkillFile, ...]


@dataclass(frozen=True)
class BundleManifest:
    schema_version: str
    bundle_id: str
    bundle_version: str
    source_revision: str
    created_at: str
    skills: tuple[ManifestSkill, ...]
    artifact_sha256: str


@dataclass(frozen=True)
class ReleaseReceipt:
    schema_version: str
    bundle_id: str
    bundle_version: str
    artifact_sha256: str
    lifecycle_state: LifecycleState
    runtime_adapter_version: str
    adk_version: str
    evaluation_receipts: tuple[str, ...]
    provenance_attestation_reference: str
    provenance_attestation_sha256: str
    approval_identity: str | None
    approved_at: str | None
    issued_at: str
    valid_until: str
    revoked_at: str | None
    revocation_reason: str | None


@dataclass(frozen=True)
class RuntimePolicy:
    allowed_skill_names: frozenset[str]
    maximum_archive_size: int
    maximum_file_count: int
    maximum_file_size: int
    allowed_path_prefixes: tuple[str, ...]
    allowed_extensions: frozenset[str]
    runtime_mode: RuntimeMode
    expected_adk_version: str
    expected_adapter_version: str
    maximum_compression_ratio: float = 100.0

    @classmethod
    def for_testing(cls, skill_names: set[str]) -> "RuntimePolicy":
        return cls(
            allowed_skill_names=frozenset(skill_names),
            maximum_archive_size=1_000_000,
            maximum_file_count=100,
            maximum_file_size=256_000,
            allowed_path_prefixes=("skills/",),
            allowed_extensions=frozenset({".md", ".json"}),
            runtime_mode="test",
            expected_adk_version="2.7.1",
            expected_adapter_version="0.1.0",
            maximum_compression_ratio=100.0,
        )


@dataclass(frozen=True)
class VerifiedSkillBundle:
    manifest: BundleManifest
    release: ReleaseReceipt
    files: Mapping[str, bytes] = field(repr=False)
    archive_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "files", MappingProxyType(dict(self.files)))

    @property
    def skill_names(self) -> tuple[str, ...]:
        return tuple(skill.name for skill in self.manifest.skills)

    def read_text(self, path: str) -> str:
        try:
            payload = self.files[path]
        except KeyError as error:
            raise KeyError(f"verified bundle has no file: {path}") from error
        return payload.decode("utf-8")
