# JovaniPink ADK

JovaniPink ADK is a Python foundation for loading reviewed, non-executable Agent Skill bundles into Google Agent Development Kit applications. It keeps a deterministic control plane between skill instructions and the tools, identities, data, and release decisions owned by a host application.

Version 0.1 is a library and synthetic reference agent. It does not publish to PyPI, deploy a service, connect to a model provider, create an MCP or A2A server, include production credentials, or contain product-specific data.

The archive boundary accepts only:

```text
manifest.json
release.json
skills/<skill-name>/SKILL.md
skills/<skill-name>/references/*.md
```

Scripts, assets, hooks, agents, plugins, binaries, dependency manifests, hidden files, symlinks, mutable source revisions, and `allowed-tools` frontmatter are rejected. Skill text cannot register a tool or grant identity, credentials, permissions, approval, release, or deployment authority.

Read [the bundle contract](docs/bundle-contract.md), [security model](docs/security.md), [threat model](docs/threat-model.md), and [synthetic example](docs/synthetic-reference-agent.md) before using the library.

Point-in-time local results are recorded separately under `evidence/`. They do not replace hosted CI or release authorization.

## Local development

```sh
uv sync --frozen
uv run --frozen mypy src tests scripts
uv run --frozen ruff check src tests scripts
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen python scripts/validate.py
```

No model API key or cloud credential is needed for the test suite.

## Status

This is a v0.1 development branch. Runtime Agent Skills and ADK tool confirmation remain experimental. Passing local tests does not establish production readiness, release status, or safe use with external write-capable tools.
