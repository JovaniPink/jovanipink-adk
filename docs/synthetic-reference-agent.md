# Synthetic Reference Agent

The synthetic support example proves the runtime boundaries without a model, network connection, cloud credential, external service, or production record. It is unsuitable for production.

The bundle contains a fictional support-policy skill. Its `SKILL.md` says to load a reference, but it does not contain the answer. The fact `18 synthetic minutes` exists only in `references/policy-facts.md`. Tests prove that the fact becomes available only when the verified reference is loaded.

The deterministic harness registers one read-only mock tool named `lookup-fictional-record`. The tool accepts one synthetic record and checks an exact tenant, user, and agent identity. The harness stores sessions only in memory and scopes them by the same identity tuple.

Adversarial tests place an instruction to call an unregistered destructive tool in:

- User input.
- A skill reference.
- Tool output.
- Retrieved content.

The observed trajectory remains exactly one call to the registered read-only mock tool. An explicit attempt to invoke the unregistered tool fails.

The harness also tests HTML escaping, cancellation before tool use, idempotent request replay, retry behavior, and a deterministic call budget. These tests demonstrate the local contract. They do not predict every model behavior or establish production safety.
