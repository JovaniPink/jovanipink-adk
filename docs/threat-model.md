# Threat Model

## Scope

This review covers the v0.1 bundle verifier, runtime adapter, and synthetic local harness. It does not cover a production deployment, real model provider, customer data, write-capable tool, or product-specific skill bundle.

## Protected assets

- User, tenant, and agent identity.
- Tool registration and tool arguments.
- Private skill instructions and references.
- Release and revocation state.
- Session and memory isolation.
- Audit and evaluation evidence.
- Cost and compute budgets.
- Rendered output consumers.

## Threats and controls

| Threat | v0.1 control | Remaining requirement |
| --- | --- | --- |
| Direct prompt injection | Skill prose cannot register tools; synthetic trajectory is fixed | Use model-level adversarial evaluation before real use |
| Indirect prompt injection | References, retrieval, and tool output are treated as untrusted data | Add contextual sanitization and destination-specific policies |
| Excessive agency | No network, cloud, deployment, or write tool exists | Keep least privilege and require external approval for writes |
| Skill supply-chain compromise | Immutable source revision, file hashes, logical artifact digest, release receipt | Add signed attestations and protected release infrastructure |
| Dependency compromise | Exact ADK pin, locked hashes, source checks, license review | Add current vulnerability intelligence and scheduled re-review |
| Memory poisoning | In-memory synthetic sessions are identity-scoped | Use authenticated, tenant-scoped storage and retention controls |
| Retrieval poisoning | Retrieved content is escaped and cannot expand the tool registry | Validate provenance, ranking, freshness, and citation behavior |
| Cross-user or tenant leakage | Synthetic records and sessions check tenant, user, and agent identity | Enforce the same checks at every production data boundary |
| Tool misuse and argument manipulation | Only host-registered names are callable | Validate each argument and destination; block SSRF and exfiltration |
| Confirmation replay | No write confirmation is used | Use durable nonce, expiration, idempotency, and replay protection |
| Cost or resource exhaustion | Archive limits and deterministic tool-call budget | Add model, token, time, retry, queue, and tenant budgets |
| Framework version drift | Exact ADK and adapter versions are verified | Re-evaluate and issue compatible receipts for every version change |
| Unsafe output rendering | Synthetic HTML output escapes untrusted inputs | Apply sink-specific escaping, CSP, and safe link handling |
| Revocation failure | Every runtime mode rejects revoked receipts | Distribute revocation state through a durable control plane |
| Emergency stopping | Synthetic cancellation fails before tool use | Add external kill switches that do not depend on model cooperation |

## Security decision

`APPROVE WITH CONDITIONS` for local library development and the synthetic reference flow only.

Conditions:

1. Do not deploy v0.1.
2. Do not accept customer-authored or marketplace bundles.
3. Do not use private data or write-capable tools.
4. Add signed provenance and durable revocation before production.
5. Add current vulnerability scanning before release acceptance.
6. Re-run this review for every ADK, adapter, archive-contract, identity, tool, or storage change.

This decision is not a security certification or a production-readiness claim.
