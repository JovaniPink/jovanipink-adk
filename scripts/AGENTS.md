# Validation-script guidance

- Scripts are deterministic evidence tooling, never a source of runtime authority.
- Preserve dependency pins and hashes, license acceptance criteria, secret detection, and publishable-file boundaries as fail-closed controls.
- Do not add provider calls, credentials, network-dependent lifecycle actions, mutable allowlists, or bundle-executed behavior.
- Keep validation reports separate from agent-behavior and ADK compatibility claims.
- Run frozen lint, type, unit, and repository-validation gates after a script change.
