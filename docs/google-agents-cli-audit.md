# Google Agents CLI Audit

Google Agents CLI is optional developer tooling. It is not a runtime dependency, package dependency, or vendored source in this repository.

The reviewed source is:

```text
Repository: https://github.com/google/agents-cli
Revision: 048578a00b0b89fc8acdbfb3501895264640f355
Version: 1.4.1
Review date: 2026-08-25
License: Apache-2.0
```

The revision contains seven Agent Skills covering ADK code, deployment, evaluation, observability, publication, scaffolding, and workflow guidance. Their content is not copied into this repository.

## Installation behavior

The inspected `agents-cli setup` command:

- Defaults to global scope.
- Can install or update the `google-agents-cli` Python tool through `uv tool install`.
- Runs `skills@1.5.9` through `npx -y` to install skills.
- Uses the mutable repository URL as the default skill source unless overridden.
- Can enter Google authentication unless `--skip-auth` is used.
- Can create compatibility links for global Antigravity skill locations.
- Provides `--dry-run`, `--workspace`, `--skills-source`, and target-agent controls.

These behaviors are broader than the needs of this library. If the tool is considered later, the safe review sequence is:

1. Review the exact immutable source revision and current package metadata.
2. Run dry-run with authentication skipped.
3. Override the skill source to an immutable, reviewed revision.
4. Use workspace scope and only named target agents.
5. Review the proposed file changes before execution.
6. Obtain separate authority before authentication, infrastructure creation, deployment, or publication.

No installation was performed during this audit.
