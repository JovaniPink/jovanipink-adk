"""A non-downloading adapter from verified bundles to ADK SkillToolset."""

from __future__ import annotations

import importlib.metadata
from collections.abc import Callable, Mapping
from typing import Any

from google.adk.skills import models
from google.adk.tools import skill_toolset
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset

from .errors import AuthorizationError, BundleVerificationError
from .frontmatter import parse_skill
from .models import VerifiedSkillBundle


class AdkRuntimeAdapter:
    """Create ADK toolsets only from immutable, already verified bundle objects."""

    VERSION = "0.1.0"
    ADK_VERSION = "2.7.1"
    CORE_TOOL_NAMES = ("list_skills", "load_skill", "load_skill_resource")

    def __init__(
        self, host_tools: Mapping[str, Callable[..., Any]] | None = None
    ) -> None:
        self._host_tools = dict(host_tools or {})
        for name, tool in self._host_tools.items():
            if not name or not callable(tool):
                raise TypeError("host tools require a non-empty name and callable")
            tool_name = getattr(tool, "name", getattr(tool, "__name__", None))
            if tool_name != name:
                raise TypeError(
                    "host tool registry keys must match callable tool names"
                )

    @property
    def registered_host_tool_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._host_tools))

    def _check_versions(self, bundle: VerifiedSkillBundle) -> None:
        installed = importlib.metadata.version("google-adk")
        if installed != self.ADK_VERSION:
            raise BundleVerificationError(
                f"installed ADK version {installed} does not match adapter version {self.ADK_VERSION}"
            )
        if bundle.release.adk_version != self.ADK_VERSION:
            raise BundleVerificationError(
                "verified bundle ADK version is incompatible with adapter"
            )
        if bundle.release.runtime_adapter_version != self.VERSION:
            raise BundleVerificationError(
                "verified bundle adapter version is incompatible with adapter"
            )

    def to_skill_toolset(
        self, bundle: VerifiedSkillBundle
    ) -> skill_toolset.SkillToolset:
        self._check_versions(bundle)
        skills: list[models.Skill] = []
        for manifest_skill in bundle.manifest.skills:
            skill_root = manifest_skill.path
            parsed = parse_skill(
                bundle.read_text(f"{skill_root}/SKILL.md"), manifest_skill.name
            )
            references: dict[str, str | bytes] = {}
            prefix = f"{skill_root}/references/"
            for path in bundle.files:
                if path.startswith(prefix):
                    references[path.removeprefix(prefix)] = bundle.read_text(path)
            skills.append(
                models.Skill(
                    frontmatter=models.Frontmatter(
                        name=parsed.name,
                        description=parsed.description,
                        license=parsed.license,
                        compatibility=parsed.compatibility,
                        metadata=parsed.metadata,
                    ),
                    instructions=parsed.instructions,
                    resources=models.Resources(
                        references=references, assets={}, scripts={}
                    ),
                )
            )
        tools: list[Callable[..., Any] | BaseTool | BaseToolset] = [
            tool for tool in self._host_tools.values()
        ]
        filter_names = list(self.CORE_TOOL_NAMES) + list(self._host_tools)
        return skill_toolset.SkillToolset(
            skills=skills,
            additional_tools=tools,
            tool_filter=filter_names,
        )

    def load_reference(
        self, bundle: VerifiedSkillBundle, skill_name: str, path: str
    ) -> str:
        if skill_name not in bundle.skill_names:
            raise AuthorizationError(f"skill is not verified: {skill_name}")
        if (
            path.startswith("/")
            or ".." in path.split("/")
            or not path.startswith("references/")
        ):
            raise AuthorizationError("reference path is outside the verified skill")
        return bundle.read_text(f"skills/{skill_name}/{path}")

    def invoke_host_tool(
        self,
        name: str,
        arguments: Mapping[str, Any],
        *,
        principal: str,
    ) -> Any:
        if name not in self._host_tools:
            raise AuthorizationError(f"host tool is not registered: {name}")
        if not principal:
            raise AuthorizationError(
                "host tool invocation requires an authenticated principal"
            )
        return self._host_tools[name](**dict(arguments))
