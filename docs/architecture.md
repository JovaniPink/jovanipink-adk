# Architecture

JovaniPink ADK has one job: turn an already verified, non-executable skill bundle into a restricted Google ADK `SkillToolset`.

The control flow is:

```text
Private skill release process
  -> immutable ZIP and release receipt
  -> host-owned RuntimePolicy
  -> verify_skill_bundle
  -> VerifiedSkillBundle
  -> AdkRuntimeAdapter
  -> restricted ADK SkillToolset
  -> host-registered tools only
```

The verifier checks the archive before ADK sees any skill content. It accepts only skill instructions and Markdown references. It rejects scripts, dependency manifests, mutable source revisions, undeclared files, and tool grants in frontmatter.

The adapter accepts only a `VerifiedSkillBundle`. It does not accept a path, URL, repository name, or branch. It cannot clone or download a bundle. It converts verified instructions and references into ADK skill models and exposes only these ADK skill tools:

- `list_skills`
- `load_skill`
- `load_skill_resource`

The adapter deliberately filters out `run_skill_script`. A host may separately register a callable tool, but the registry name must match the callable name. Skill content cannot add a tool or change that registry.

## Trust boundaries

The bundle is untrusted until verification completes. A verified bundle is still instruction content, not authority. The host application remains responsible for:

- User, tenant, and agent identity.
- Tool registration and argument policy.
- Data authorization.
- Network controls.
- Release and revocation state.
- Durable approval for external side effects.
- Audit records, idempotency, and replay protection.

The release receipt is evidence consumed by policy. It is not a signature format in v0.1. A production design must add a durable attestation and signature verification mechanism before accepting real private bundles.

## Non-goals

Version 0.1 does not provide deployment, a model-backed agent, cloud storage, a package registry, an MCP server, an A2A service, or write-capable tools. It does not claim production readiness.
