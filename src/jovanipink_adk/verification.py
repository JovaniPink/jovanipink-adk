"""Fail-closed verification for content-addressed, non-executable skill archives."""

from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import cast

from .errors import BundleVerificationError
from .frontmatter import SKILL_NAME, parse_skill
from .models import (
    BundleManifest,
    LifecycleState,
    ManifestSkill,
    ReleaseReceipt,
    RuntimePolicy,
    SkillFile,
    VerifiedSkillBundle,
)


SHA256 = re.compile(r"^[0-9a-f]{64}$")
REVISION = re.compile(r"^[0-9a-f]{40}$")
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "bundle_id",
        "bundle_version",
        "source_revision",
        "created_at",
        "skills",
        "artifact_sha256",
    }
)
SKILL_FIELDS = frozenset({"name", "path", "files"})
FILE_FIELDS = frozenset({"path", "sha256"})
RELEASE_FIELDS = frozenset(
    {
        "schema_version",
        "bundle_id",
        "bundle_version",
        "artifact_sha256",
        "lifecycle_state",
        "runtime_adapter_version",
        "adk_version",
        "evaluation_receipts",
        "provenance_attestation_reference",
        "provenance_attestation_sha256",
        "approval_identity",
        "approved_at",
        "issued_at",
        "valid_until",
        "revoked_at",
        "revocation_reason",
    }
)
ALLOWED_TOP_LEVEL = frozenset({"manifest.json", "release.json"})


def _object(value: object, label: str, fields: frozenset[str]) -> dict[str, object]:
    if not isinstance(value, dict):
        raise BundleVerificationError(f"{label} must be an object")
    unknown = sorted(set(value) - fields)
    missing = sorted(fields - set(value))
    if unknown:
        raise BundleVerificationError(f"{label} has unknown field: {unknown[0]}")
    if missing:
        raise BundleVerificationError(f"{label} is missing field: {missing[0]}")
    return value


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise BundleVerificationError(f"{label} must be a non-empty string")
    return value


def _optional_string(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _string(value, label)


def _timestamp(value: object, label: str) -> str:
    text = _string(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise BundleVerificationError(
            f"{label} must be an ISO-8601 timestamp"
        ) from error
    if parsed.tzinfo is None:
        raise BundleVerificationError(f"{label} must include a timezone")
    return text


def _json(payload: bytes, label: str) -> object:
    try:
        return json.loads(payload.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise BundleVerificationError(f"{label} is not valid UTF-8") from error
    except json.JSONDecodeError as error:
        raise BundleVerificationError(f"{label} is not valid JSON") from error


def parse_manifest(payload: bytes) -> BundleManifest:
    value = _object(_json(payload, "manifest.json"), "manifest", MANIFEST_FIELDS)
    schema_version = _string(value["schema_version"], "manifest schema version")
    if schema_version != "1":
        raise BundleVerificationError("unsupported manifest schema version")
    bundle_id = _string(value["bundle_id"], "bundle ID")
    if not OPAQUE_ID.fullmatch(bundle_id):
        raise BundleVerificationError("invalid opaque bundle ID")
    bundle_version = _string(value["bundle_version"], "bundle version")
    if not SEMVER.fullmatch(bundle_version):
        raise BundleVerificationError("bundle version must use SemVer")
    source_revision = _string(value["source_revision"], "source revision")
    if not REVISION.fullmatch(source_revision):
        raise BundleVerificationError(
            "source revision must be an immutable 40-character Git SHA"
        )
    created_at = _timestamp(value["created_at"], "manifest creation time")
    artifact_sha256 = _string(value["artifact_sha256"], "artifact SHA-256")
    if not SHA256.fullmatch(artifact_sha256):
        raise BundleVerificationError("artifact SHA-256 is invalid")
    raw_skills = value["skills"]
    if not isinstance(raw_skills, list) or not raw_skills:
        raise BundleVerificationError("manifest skills must be a non-empty array")
    skills: list[ManifestSkill] = []
    for index, raw_skill in enumerate(raw_skills):
        skill = _object(raw_skill, f"manifest skill {index}", SKILL_FIELDS)
        name = _string(skill["name"], "skill name")
        if not SKILL_NAME.fullmatch(name) or len(name) > 64:
            raise BundleVerificationError(f"invalid skill name: {name}")
        path = _string(skill["path"], "skill path")
        if path != f"skills/{name}":
            raise BundleVerificationError("manifest skill path does not match its name")
        raw_files = skill["files"]
        if not isinstance(raw_files, list) or not raw_files:
            raise BundleVerificationError(
                "manifest skill files must be a non-empty array"
            )
        files: list[SkillFile] = []
        for raw_file in raw_files:
            file_value = _object(raw_file, f"manifest file for {name}", FILE_FIELDS)
            file_path = _string(file_value["path"], "manifest file path")
            digest = _string(file_value["sha256"], "manifest file SHA-256")
            if not SHA256.fullmatch(digest):
                raise BundleVerificationError("manifest file SHA-256 is invalid")
            files.append(SkillFile(file_path, digest))
        skills.append(ManifestSkill(name, path, tuple(files)))
    names = [skill.name for skill in skills]
    if len(names) != len(set(names)):
        raise BundleVerificationError("manifest contains a duplicate skill")
    return BundleManifest(
        schema_version,
        bundle_id,
        bundle_version,
        source_revision,
        created_at,
        tuple(skills),
        artifact_sha256,
    )


def parse_release(payload: bytes) -> ReleaseReceipt:
    value = _object(_json(payload, "release.json"), "release receipt", RELEASE_FIELDS)
    state_value = _string(value["lifecycle_state"], "lifecycle state")
    if state_value not in {"reviewed", "evaluated", "released", "revoked"}:
        raise BundleVerificationError("invalid lifecycle state")
    state = cast(LifecycleState, state_value)
    receipts = value["evaluation_receipts"]
    if not isinstance(receipts, list) or not all(
        isinstance(item, str) and item for item in receipts
    ):
        raise BundleVerificationError("evaluation receipts must be a string array")
    digest = _string(value["artifact_sha256"], "release artifact SHA-256")
    attestation_digest = _string(
        value["provenance_attestation_sha256"], "provenance attestation SHA-256"
    )
    if not SHA256.fullmatch(digest) or not SHA256.fullmatch(attestation_digest):
        raise BundleVerificationError("release receipt contains an invalid SHA-256")
    return ReleaseReceipt(
        schema_version=_string(value["schema_version"], "release schema version"),
        bundle_id=_string(value["bundle_id"], "release bundle ID"),
        bundle_version=_string(value["bundle_version"], "release bundle version"),
        artifact_sha256=digest,
        lifecycle_state=state,
        runtime_adapter_version=_string(
            value["runtime_adapter_version"], "runtime adapter version"
        ),
        adk_version=_string(value["adk_version"], "ADK version"),
        evaluation_receipts=tuple(receipts),
        provenance_attestation_reference=_string(
            value["provenance_attestation_reference"],
            "provenance attestation reference",
        ),
        provenance_attestation_sha256=attestation_digest,
        approval_identity=_optional_string(
            value["approval_identity"], "approval identity"
        ),
        approved_at=(
            None
            if value["approved_at"] is None
            else _timestamp(value["approved_at"], "approval time")
        ),
        issued_at=_timestamp(value["issued_at"], "receipt issue time"),
        valid_until=_timestamp(value["valid_until"], "receipt expiration time"),
        revoked_at=(
            None
            if value["revoked_at"] is None
            else _timestamp(value["revoked_at"], "revocation time")
        ),
        revocation_reason=_optional_string(
            value["revocation_reason"], "revocation reason"
        ),
    )


def canonical_artifact_sha256(manifest: BundleManifest, files: dict[str, bytes]) -> str:
    """Hash the complete logical payload while excluding its self-referential digest field."""

    identity = {
        "schema_version": manifest.schema_version,
        "bundle_id": manifest.bundle_id,
        "bundle_version": manifest.bundle_version,
        "source_revision": manifest.source_revision,
        "created_at": manifest.created_at,
        "skills": [
            {
                "name": skill.name,
                "path": skill.path,
                "files": [
                    {"path": item.path, "sha256": item.sha256} for item in skill.files
                ],
            }
            for skill in manifest.skills
        ],
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    for path in sorted(files):
        encoded = path.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(len(files[path]).to_bytes(8, "big"))
        digest.update(files[path])
    return digest.hexdigest()


def _path_error(path: str) -> str | None:
    if path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        return "absolute path"
    if "\\" in path:
        return "non-POSIX path"
    pure = PurePosixPath(path)
    if any(part == ".." for part in pure.parts):
        return "path traversal"
    if any(part.startswith(".") for part in pure.parts):
        return "hidden file"
    if not path or path.endswith("/"):
        return "directory entry"
    return None


def _allowed_skill_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    if len(parts) == 3 and parts[0] == "skills" and parts[2] == "SKILL.md":
        return True
    return (
        len(parts) == 4
        and parts[0] == "skills"
        and parts[2] == "references"
        and parts[3].endswith(".md")
    )


def _validate_archive_entries(
    payload: bytes, archive: zipfile.ZipFile, policy: RuntimePolicy
) -> list[zipfile.ZipInfo]:
    if len(payload) > policy.maximum_archive_size:
        raise BundleVerificationError("archive size exceeds policy")
    entries = archive.infolist()
    if len(entries) > policy.maximum_file_count:
        raise BundleVerificationError("archive file count exceeds policy")
    names = [entry.filename for entry in entries]
    if len(names) != len(set(names)):
        raise BundleVerificationError("archive contains a duplicate entry")
    folded: dict[str, str] = {}
    for name in names:
        previous = folded.get(name.casefold())
        if previous is not None and previous != name:
            raise BundleVerificationError("archive contains case-colliding paths")
        folded[name.casefold()] = name
    for entry in entries:
        path_error = _path_error(entry.filename)
        if path_error:
            raise BundleVerificationError(
                f"archive contains {path_error}: {entry.filename}"
            )
        mode = entry.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise BundleVerificationError(
                f"archive contains a symlink: {entry.filename}"
            )
        if entry.flag_bits & 0x1:
            raise BundleVerificationError("encrypted archive entries are not accepted")
        if entry.file_size > policy.maximum_file_size:
            raise BundleVerificationError(f"file size exceeds policy: {entry.filename}")
        ratio = entry.file_size / max(entry.compress_size, 1)
        if ratio > policy.maximum_compression_ratio:
            raise BundleVerificationError(
                f"compression ratio exceeds policy: {entry.filename}"
            )
        if entry.filename not in ALLOWED_TOP_LEVEL and not _allowed_skill_path(
            entry.filename
        ):
            raise BundleVerificationError(f"forbidden archive path: {entry.filename}")
        if entry.filename not in ALLOWED_TOP_LEVEL:
            if not any(
                entry.filename.startswith(prefix)
                for prefix in policy.allowed_path_prefixes
            ):
                raise BundleVerificationError(
                    f"archive path is outside the runtime policy: {entry.filename}"
                )
            suffix = PurePosixPath(entry.filename).suffix
            if suffix not in policy.allowed_extensions:
                raise BundleVerificationError(
                    f"archive extension is outside the runtime policy: {entry.filename}"
                )
    return entries


def _parse_time(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def verify_skill_bundle(
    payload: bytes,
    policy: RuntimePolicy,
    *,
    now: datetime | None = None,
) -> VerifiedSkillBundle:
    if policy.runtime_mode not in {"test", "production"}:
        raise BundleVerificationError("runtime mode must be test or production")
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload), "r")
    except zipfile.BadZipFile as error:
        raise BundleVerificationError("bundle is not a valid ZIP archive") from error
    with archive:
        entries = _validate_archive_entries(payload, archive, policy)
        files: dict[str, bytes] = {}
        for entry in entries:
            try:
                content = archive.read(entry)
            except (RuntimeError, zipfile.BadZipFile) as error:
                raise BundleVerificationError(
                    f"cannot read archive entry: {entry.filename}"
                ) from error
            if len(content) != entry.file_size:
                raise BundleVerificationError(
                    f"archive size mismatch: {entry.filename}"
                )
            files[entry.filename] = content
    if set(ALLOWED_TOP_LEVEL) - set(files):
        raise BundleVerificationError(
            "archive must contain manifest.json and release.json"
        )
    for path, content in files.items():
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise BundleVerificationError(
                f"archive entry is not valid UTF-8: {path}"
            ) from error
        if "\x00" in text:
            raise BundleVerificationError(f"archive entry contains a NUL byte: {path}")
    manifest = parse_manifest(files["manifest.json"])
    release = parse_release(files["release.json"])
    if release.schema_version != "1":
        raise BundleVerificationError("unsupported release receipt schema version")
    if release.lifecycle_state == "revoked":
        raise BundleVerificationError("bundle release is revoked")
    if (
        release.bundle_id != manifest.bundle_id
        or release.bundle_version != manifest.bundle_version
    ):
        raise BundleVerificationError("release receipt does not match bundle identity")
    if release.artifact_sha256 != manifest.artifact_sha256:
        raise BundleVerificationError(
            "release receipt does not match artifact identity"
        )
    if release.adk_version != policy.expected_adk_version:
        raise BundleVerificationError(
            "release ADK version is incompatible with runtime policy"
        )
    if release.runtime_adapter_version != policy.expected_adapter_version:
        raise BundleVerificationError(
            "release adapter version is incompatible with runtime policy"
        )
    current = now or datetime.now(timezone.utc)
    if _parse_time(release.valid_until) <= current:
        raise BundleVerificationError("release receipt has expired")
    if policy.runtime_mode == "production" and release.lifecycle_state != "released":
        raise BundleVerificationError("production mode accepts only released bundles")
    if release.lifecycle_state == "released":
        if not release.evaluation_receipts:
            raise BundleVerificationError(
                "released bundle is missing evaluation evidence"
            )
        if (
            not release.provenance_attestation_reference
            or not release.provenance_attestation_sha256
        ):
            raise BundleVerificationError(
                "released bundle is missing provenance attestation evidence"
            )
        if not release.approval_identity or not release.approved_at:
            raise BundleVerificationError(
                "released bundle is missing approval evidence"
            )
    if release.revoked_at or release.revocation_reason:
        raise BundleVerificationError(
            "non-revoked receipt contains revocation information"
        )
    declared: dict[str, str] = {}
    for skill in manifest.skills:
        if skill.name not in policy.allowed_skill_names:
            raise BundleVerificationError(
                f"skill is not allowed by runtime policy: {skill.name}"
            )
        for item in skill.files:
            if item.path in declared:
                raise BundleVerificationError(
                    f"manifest declares a duplicate file: {item.path}"
                )
            if not item.path.startswith(skill.path + "/"):
                raise BundleVerificationError(
                    "manifest file is outside its declared skill path"
                )
            declared[item.path] = item.sha256
    actual_skill_paths = set(files) - ALLOWED_TOP_LEVEL
    if set(declared) != actual_skill_paths:
        extras = sorted(actual_skill_paths - set(declared))
        missing = sorted(set(declared) - actual_skill_paths)
        label = extras[0] if extras else missing[0]
        raise BundleVerificationError(f"undeclared or missing archive file: {label}")
    for path, expected in declared.items():
        observed = hashlib.sha256(files[path]).hexdigest()
        if observed != expected:
            raise BundleVerificationError(f"hash mismatch for {path}")
    for skill in manifest.skills:
        skill_path = f"{skill.path}/SKILL.md"
        if skill_path not in files:
            raise BundleVerificationError(f"skill is missing SKILL.md: {skill.name}")
        parse_skill(files[skill_path].decode("utf-8"), skill.name)
    logical_files = {path: files[path] for path in sorted(declared)}
    observed_artifact = canonical_artifact_sha256(manifest, logical_files)
    if observed_artifact != manifest.artifact_sha256:
        raise BundleVerificationError("artifact hash mismatch")
    return VerifiedSkillBundle(
        manifest=manifest,
        release=release,
        files=files,
        archive_sha256=hashlib.sha256(payload).hexdigest(),
    )
