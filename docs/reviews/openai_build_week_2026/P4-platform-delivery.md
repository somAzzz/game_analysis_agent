# P4 platform delivery review

Status: **partial**

Date: 2026-07-16

Machine: macOS 26.5.2, Apple Silicon arm64

Reviewed source: `73f4274dcb153570c69733a2e4deb42ea43253ec`

The macOS-native evaluator path is now real: standard-library Inspect, locked
Replay, twice-repeated offline setup, production frontend build, and the
same-origin Judge UI/API all passed. The doctor correctly separates the native
dashboard from its Docker delivery and returns an unsupported exit for the
latter on this host.

This is not yet a cross-platform pass. Docker is absent, the locally discovered
Godot is 4.7 instead of the pinned 4.4 release, and no OpenAI key is configured.
Those facts leave the macOS container, fresh pinned-Godot, and live campaign
checks `not_run`. The Linux amd64 job now executes native Inspect/Replay, builds
the CPU image, runs read-only/networkless container checks, smokes the UI/API,
and uploads the evidence—but that workflow must run after the commit is pushed
before it becomes Linux evidence. Linux arm64 also remains a packaging target,
not a tested claim.

Machine-readable details and remediation are in
`P4-platform-delivery.review.json`. G4 must remain open until the pending rows
are replaced by dated run records rather than source inspection.
