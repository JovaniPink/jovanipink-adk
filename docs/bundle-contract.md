# Bundle Contract

Version 0.1 accepts one deterministic ZIP layout:

```text
manifest.json
release.json
skills/<skill-name>/SKILL.md
skills/<skill-name>/references/*.md
```

Every skill and reference file must be declared in `manifest.json` with a SHA-256 value. Every declared file must exist, and every archive file must be declared. Skill names follow the Agent Skills lowercase and hyphenated naming convention.

## Artifact identity

An archive cannot contain a literal hash of its complete raw ZIP bytes without creating a self-reference. The `artifact_sha256` field therefore identifies the complete logical skill payload, not the raw ZIP container.

The logical digest covers:

1. Manifest identity fields and every declared path and file digest.
2. Every declared skill file path and exact file bytes in sorted order.
3. Length prefixes for paths and byte payloads to prevent ambiguous concatenation.

The digest excludes only the self-referential `artifact_sha256` field and the release receipt. The receipt repeats and binds the logical digest. `VerifiedSkillBundle.archive_sha256` separately records the raw ZIP SHA-256 for transport and audit evidence.

Changing a skill byte, reference byte, declared path, source revision, bundle identity, version, or timestamp changes the logical artifact digest. Changing ZIP compression or entry metadata changes the raw ZIP digest without changing the logical artifact identity.

## Manifest requirements

`manifest.json` records:

- Schema version `1`.
- An opaque bundle ID.
- A SemVer bundle version.
- An exact 40-character Git revision.
- A timezone-aware creation timestamp.
- Skill names, paths, file paths, and file hashes.
- The logical artifact SHA-256.

Unknown fields are rejected. A branch, tag, symbolic revision, or shortened Git SHA is rejected.

## Release receipt requirements

`release.json` binds the bundle and artifact identity to:

- Lifecycle state: `reviewed`, `evaluated`, `released`, or `revoked`.
- Exact adapter and ADK versions.
- Evaluation receipt references.
- A provenance attestation reference and digest.
- Approval identity and time when released.
- Issue and expiration times.
- Revocation information when applicable.

Test mode may accept reviewed or evaluated bundles. Production mode accepts only released bundles. Every mode rejects revoked, expired, or incompatible bundles.

The JSON schemas under `schemas/` document the wire format. Runtime verification remains authoritative and adds cross-field and policy checks that JSON Schema alone cannot express.
