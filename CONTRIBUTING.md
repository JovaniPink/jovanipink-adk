# Contributing

Contributions must preserve the separation between instruction content and deterministic authority.

- Keep the archive instruction-and-reference-only.
- Do not add scripts, hooks, plugins, agents, deployment files, credentials, private product facts, or write-capable example tools.
- Do not make the adapter download repositories or mutable remote content.
- Add failing tests before changing a security boundary.
- Use synthetic examples only.
- Keep authored content in approachable US English and ASCII.
- Run `uv run --frozen python scripts/validate.py` before requesting review.

Any change to ADK, archive formats, identity, tool registration, release state, or revocation needs explicit security review.
