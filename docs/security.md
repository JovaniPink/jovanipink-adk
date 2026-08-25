# Security Model

Skill content is untrusted instruction input. It can influence model behavior, so mounting it expands the agent trust boundary. It cannot grant identity, credentials, tools, network access, data access, approval, release status, deployment authority, or publication authority.

## Fail-closed archive verification

The verifier rejects:

- Scripts, assets, hooks, agents, plugins, executables, binaries, and dependency manifests.
- `allowed-tools` in skill frontmatter.
- Symlinks, absolute paths, traversal, backslash paths, hidden files, duplicate entries, and case-colliding paths.
- Encrypted entries, invalid UTF-8, NUL bytes, undeclared files, missing files, and hash mismatches.
- Excessive archive size, file count, file size, or compression ratio.
- Mutable source revisions, unknown schema fields, expired receipts, revoked bundles, and incompatible versions.
- Production use of a bundle that is not explicitly released.

`RuntimePolicy` narrows the accepted skill names, paths, extensions, sizes, versions, and runtime mode. The hard archive contract remains in force even if a policy is accidentally broad.

## Tool boundary

The ADK runtime skill interface can expose skill resource and script facilities. Version 0.1 exposes listing and loading only. It never exposes the skill script runner.

Host tools are separate Python callables registered by the application. The adapter checks exact names, and its direct invocation helper requires an authenticated principal string. A production host must add structured identity, authorization for each argument, network restrictions, idempotency, and durable audit evidence.

## Approval boundary

Google ADK tool confirmation is experimental. It may be useful in demonstrations, but it is not a durable production approval system. Real external writes eventually require authenticated approvers, external durable state, idempotency keys, replay protection, expiration, revocation, and an auditable decision record.

## Dependency boundary

The runtime dependency is exactly `google-adk==2.7.1`. The lockfile records artifact hashes for the full dependency graph. Any ADK or adapter version change invalidates existing release compatibility and requires review.

The test suite needs no cloud credential or model API key. CI has read-only repository permissions and does not deploy or publish. It bootstraps uv from a versioned and SHA-256-locked Linux wheel, then runs strict typing and linting from the locked environment.

The source distribution contains only the package source, license, README, project metadata, generated package metadata, and the non-sensitive `.gitignore` that Hatchling uses to preserve VCS exclusion rules. Repository CI, evidence, provenance, tests, lockfiles, validation scripts, and other Git control files remain reviewable in Git but are not bundled into the distributable archive. The artifact scanner enforces this exact boundary.

## Reporting a vulnerability

Follow [SECURITY.md](../SECURITY.md). Do not place secrets, private product details, or proof-of-concept customer data in a public issue.
