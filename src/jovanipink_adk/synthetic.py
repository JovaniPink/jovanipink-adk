"""Synthetic, local-only fixtures for testing runtime boundaries."""

from __future__ import annotations

import hashlib
import html
import io
import json
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass

from .errors import AuthorizationError, BudgetExceededError, CancellationRequestedError
from .models import BundleManifest, LifecycleState, ManifestSkill, SkillFile
from .verification import canonical_artifact_sha256


DEFAULT_SKILL = """---
name: fictional-support-policy
description: Answer questions about a fictional support policy using its reference file.
license: MIT
---
Load `references/policy-facts.md` before answering a question about the fictional policy. Use only synthetic records and do not request or invoke a tool that the host did not register.
"""
DEFAULT_REFERENCE = b"The fictional policy response target is 18 synthetic minutes.\n"


def _json_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def build_synthetic_bundle(
    *,
    lifecycle_state: LifecycleState = "evaluated",
    valid_until: str = "2099-01-01T00:00:00Z",
    adk_version: str = "2.7.1",
    skill_name: str = "fictional-support-policy",
    skill_content: str = DEFAULT_SKILL,
    reference_content: bytes = DEFAULT_REFERENCE,
) -> bytes:
    """Build a deterministic synthetic archive. It is unsuitable for production."""

    skill_path = f"skills/{skill_name}/SKILL.md"
    reference_path = f"skills/{skill_name}/references/policy-facts.md"
    payload_files = {
        skill_path: skill_content.encode("utf-8"),
        reference_path: reference_content,
    }
    file_records = tuple(
        SkillFile(path, hashlib.sha256(content).hexdigest())
        for path, content in sorted(payload_files.items())
    )
    provisional = BundleManifest(
        schema_version="1",
        bundle_id="synthetic-support-bundle",
        bundle_version="0.1.0",
        source_revision="1" * 40,
        created_at="2026-08-25T00:00:00Z",
        skills=(ManifestSkill(skill_name, f"skills/{skill_name}", file_records),),
        artifact_sha256="0" * 64,
    )
    artifact_sha256 = canonical_artifact_sha256(provisional, payload_files)
    manifest = {
        "schema_version": provisional.schema_version,
        "bundle_id": provisional.bundle_id,
        "bundle_version": provisional.bundle_version,
        "source_revision": provisional.source_revision,
        "created_at": provisional.created_at,
        "skills": [
            {
                "name": skill_name,
                "path": f"skills/{skill_name}",
                "files": [
                    {"path": item.path, "sha256": item.sha256} for item in file_records
                ],
            }
        ],
        "artifact_sha256": artifact_sha256,
    }
    revoked = lifecycle_state == "revoked"
    release = {
        "schema_version": "1",
        "bundle_id": provisional.bundle_id,
        "bundle_version": provisional.bundle_version,
        "artifact_sha256": artifact_sha256,
        "lifecycle_state": lifecycle_state,
        "runtime_adapter_version": "0.1.0",
        "adk_version": adk_version,
        "evaluation_receipts": ["evaluation:synthetic-reference-v1"],
        "provenance_attestation_reference": "attestation:synthetic-reference-v1",
        "provenance_attestation_sha256": hashlib.sha256(
            b"synthetic attestation"
        ).hexdigest(),
        "approval_identity": "synthetic-approver"
        if lifecycle_state == "released"
        else None,
        "approved_at": "2026-08-25T00:00:00Z"
        if lifecycle_state == "released"
        else None,
        "issued_at": "2026-08-25T00:00:00Z",
        "valid_until": valid_until,
        "revoked_at": "2026-08-25T00:00:00Z" if revoked else None,
        "revocation_reason": "synthetic revocation" if revoked else None,
    }
    all_files = {
        "manifest.json": _json_bytes(manifest),
        "release.json": _json_bytes(release),
        **payload_files,
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for path, content in sorted(all_files.items()):
            archive.writestr(_zip_info(path), content)
    return output.getvalue()


@dataclass(frozen=True)
class SyntheticPrincipal:
    user_id: str
    tenant_id: str
    agent_id: str = "synthetic-support-agent"


@dataclass(frozen=True)
class SyntheticResult:
    rendered_output: str
    tool_trajectory: tuple[str, ...]
    record: tuple[tuple[str, str], ...]


class SyntheticSupportAgent:
    """A deterministic local harness, not a production or model-backed agent."""

    def __init__(self, max_tool_calls: int = 100) -> None:
        self._maximum = max_tool_calls
        self._effects = 0
        self._results: dict[str, SyntheticResult] = {}
        self._sessions: dict[tuple[str, str, str, str], SyntheticResult] = {}
        self._canceled: set[str] = set()

    @property
    def registered_tool_names(self) -> tuple[str, ...]:
        return ("lookup-fictional-record",)

    @property
    def effect_count(self) -> int:
        return self._effects

    def cancel(self, request_id: str) -> None:
        self._canceled.add(request_id)

    def _lookup(
        self, principal: SyntheticPrincipal, record_id: str
    ) -> tuple[tuple[str, str], ...]:
        if (
            principal.tenant_id != "tenant-a"
            or principal.user_id != "user-a"
            or principal.agent_id != "synthetic-support-agent"
        ):
            raise AuthorizationError(
                "synthetic record is not authorized for this principal"
            )
        if record_id != "case-100":
            raise AuthorizationError(
                "synthetic record is outside the deterministic allowlist"
            )
        return (("record_id", "case-100"), ("status", "fictional-open"))

    def respond(
        self,
        *,
        principal: SyntheticPrincipal,
        session_id: str,
        user_input: str,
        retrieved_content: str,
        untrusted_tool_output: str = "",
        request_id: str,
    ) -> SyntheticResult:
        if request_id in self._canceled:
            raise CancellationRequestedError(f"request was canceled: {request_id}")
        if request_id in self._results:
            return self._results[request_id]
        if self._effects >= self._maximum:
            raise BudgetExceededError("synthetic tool-call budget is exhausted")
        record = self._lookup(principal, "case-100")
        self._effects += 1
        safe_input = html.escape(user_input, quote=True)
        safe_retrieval = html.escape(retrieved_content, quote=True)
        safe_tool_output = html.escape(untrusted_tool_output, quote=True)
        rendered = (
            f"<p>Request: {safe_input}</p>"
            f"<p>Retrieved context treated as data: {safe_retrieval}</p>"
            f"<p>Untrusted tool output treated as data: {safe_tool_output}</p>"
            "<p>Fictional record case-100 is fictional-open.</p>"
        )
        result = SyntheticResult(rendered, ("lookup-fictional-record",), record)
        self._results[request_id] = result
        self._sessions[
            (principal.tenant_id, principal.user_id, principal.agent_id, session_id)
        ] = result
        return result

    def read_session(
        self, principal: SyntheticPrincipal, session_id: str
    ) -> SyntheticResult:
        key = (principal.tenant_id, principal.user_id, principal.agent_id, session_id)
        if key in self._sessions:
            return self._sessions[key]
        if any(stored[3] == session_id for stored in self._sessions):
            raise AuthorizationError("session is owned by another principal")
        raise KeyError(session_id)
