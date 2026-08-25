# Evaluation

Agent evaluation must inspect both the final answer and the path used to produce it. A plausible final answer does not excuse an unsafe tool call, and a correct tool trajectory does not excuse an incorrect or misleading answer.

The v0.1 synthetic suite records:

- Final rendered output.
- Ordered tool-use trajectory.
- Returned synthetic record.
- Identity and session boundary outcomes.
- Cancellation, idempotency, retry, and budget behavior.

The required end-to-end case verifies a bundle, creates an ADK `SkillToolset`, confirms that `run_skill_script` is absent, loads a fact found only in a reference, and rejects an unregistered tool request.

Before a real private bundle can enter a released state, its release process must record immutable evaluation receipt references and a provenance attestation digest. A production evaluation suite must add model-backed tests, multiple prompt-injection sources, retrieval quality, tool argument validation, failure behavior, latency, cost, and client or framework version evidence.

Passing synthetic tests is not permission to release or deploy.
