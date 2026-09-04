# Repository guidance

- This repository verifies and loads immutable reviewed skill bundles into a restricted Google ADK host. It is not a generic behavioral evaluation system.
- A runtime pass establishes compatibility only; it does not prove that a skill improves Codex, Claude, Work, or any other agent.
- The host owns identity, tenant scope, tool registration, permissions, data access, model selection, budgets, release policy, and deployment.
- Bundles must not create tools, expand permissions, introduce hidden executables, use mutable references, or gain release authority.
- Before modifying a subtree, inspect its applicable `AGENTS.md`; start specialized work from that directory when its local guidance must enter the initial instruction chain.
- Run the frozen type, lint, unit, and repository validation gates before describing the adapter as compatible.
