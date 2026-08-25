# Release Process

Version numbers, release state, publication, and deployment are separate decisions.

For a future library release:

1. Start from a clean checkout of an exact source revision.
2. Synchronize the committed lockfile with `uv sync --frozen`.
3. Run `python scripts/validate.py` without cloud credentials or model API keys.
4. Review dependency and vulnerability results, licenses, source provenance, and public-boundary findings.
5. Build artifacts in an isolated environment and record their SHA-256 values.
6. Review the complete diff and generated artifacts.
7. Obtain explicit release authorization.
8. Tag only the exact reviewed commit.
9. Publish only through a separately authorized process.
10. Verify the remote tag and published artifact independently.

Version 0.1 does not publish to PyPI or deploy a service. The existence of a version in `pyproject.toml` does not mean it is released.

For runtime skill bundles, `reviewed`, `evaluated`, `released`, and `revoked` are distinct states. Only the owning private release process can produce approval evidence. The adapter cannot promote a bundle between states.
