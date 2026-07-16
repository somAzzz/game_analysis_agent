# P4 Restricted-Environment Review

- Decision: **passed for repository-only Judge Mode**
- Reviewed commit: `4b2badfe66d7ff91bb0fa87ebca7cd2243ded797`
- Host: macOS Darwin 25.5.0 arm64
- System Python: 3.9.6
- Locked Replay Python: 3.12
- Docker: **unavailable — not run**

## Result

Dependency-free Inspect and locked offline Replay pass with no network, Docker
socket, GPU, API key, TTY, browser, available port, or sibling game checkout.
Failure injection covers missing/tampered artifacts, mismatched claims,
unsupported Python, missing `uv`, timeout, SIGTERM, and a mid-run provider
failure. Timeout and SIGTERM both terminate the worker and its descendant
process group.

The observed development-host durations were 4.775 ms for Inspect and 267.661
ms for Replay. Focused Judge tests passed 18/18; the full Python suite passed
404/404 and Ruff passed.

## Explicit limitation

The `linux/amd64` `openai/codex-universal` approximation was not run because
this host has no Docker executable. This is a warning for the later
cross-platform gate, not evidence of Linux support and not a false project
failure. The exact canonical commands must still be run in pinned Linux CI
before G4 can make that platform claim.
