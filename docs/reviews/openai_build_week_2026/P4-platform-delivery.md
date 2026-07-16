# P4 platform delivery review

Status: **partial**

Date: 2026-07-16

Machine: macOS 26.5.2, Apple Silicon arm64

Reviewed source: `2b6cf16978065759c81b8f6937eaa71ce685bc48`

The macOS-native evaluator path is now real: standard-library Inspect, locked
Replay, twice-repeated offline setup, production frontend build, and the
same-origin Judge UI/API all passed. The doctor correctly separates the native
dashboard from its Docker delivery and returns an unsupported exit for the
latter on this host.

The release-revision macOS rerun now also proves the project-local,
SHA-512-pinned Godot 4.4 runtime with a clean-worktree two-run/four-week fresh
trace. The exact command set and result digests are retained in
`platform-evidence/macos-native.json`.

This is not yet a cross-platform pass. Docker is absent and no OpenAI key is
configured. Docker evidence is assigned to the Linux path. The Linux amd64 job
now executes native Inspect/Replay, builds the CPU
image, runs read-only/networkless container checks, smokes the UI/API, and
uploads the evidence—but it must run from a PR, `main`, or manual dispatch
before it becomes evidence. The separate real-Godot job must also run with
`4.4-stable`. Linux arm64 remains a packaging target, not a tested claim.

Machine-readable details and remediation are in
`P4-platform-delivery.review.json`. G4 must remain open until the pending rows
are replaced by dated run records rather than source inspection.
