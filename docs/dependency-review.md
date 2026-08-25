# Dependency Review

Version 0.1 has one direct runtime dependency: `google-adk==2.7.1`. The project requires Python 3.11 or newer and uses `uv` with a committed lockfile. Development tools are pinned separately: `hatchling==1.27.0`, `mypy==1.20.2`, `pip-audit==2.10.1`, `ruff==0.15.12`, and `types-jsonschema==4.26.0.20260518`.

The reviewed Google ADK wheel has SHA-256:

```text
cd21e37c9846a80086fd880924aa5548e625ef85178122b40cda81ef5316129f
```

The lockfile contains the exact ADK wheel and source-distribution hashes plus hashes for every transitive registry artifact. The dependency review rejects Git, path, URL, or unpinned direct sources other than this repository's editable local package.

The Linux CI runner bootstraps `uv==0.12.3` from `requirements-bootstrap-linux.txt`. That file permits binary wheels only and requires the reviewed wheel SHA-256. The lock is platform-specific and is not presented as a portable local development environment.

The installed license scan accepts only reviewed permissive license signals, including Apache, BSD, ISC, MIT, MPL, and PSF families. It rejects GPL, AGPL, SSPL, proprietary, commercial-only, missing, or unknown signals. This is an engineering control, not legal advice.

Changing ADK changes a security boundary. Every version update must review:

- SkillToolset constructor and tool names.
- Resource and script-loading behavior.
- Tool confirmation behavior.
- Model, session, memory, retrieval, and tool APIs used by the host.
- Dependency graph, hashes, licenses, and vulnerability intelligence.
- Existing bundle receipt compatibility.

No dependency is automatically repinned after an upstream change.

CI also runs `pip-audit==2.10.1` against the installed locked environment and stores the JSON result as short-lived validation evidence. This online result is time-sensitive. A clean result means that the selected advisory service reported no known vulnerability at that time; it does not prove that the graph has no vulnerability.
