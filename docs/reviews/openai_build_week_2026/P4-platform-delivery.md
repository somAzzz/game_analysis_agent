# P4 platform delivery review

Status: **partial**

Date: 2026-07-16

Machine: macOS 26.5.2, Apple Silicon arm64

Reviewed source: `be56673fea66155e5eec93d2bcfa5a7a76ce10e0`

Delivery contract: `6fd5874d2f0b6d29adc1aec90a35696c2631116d5d00d16973685ccb1466194a`

The macOS-native evaluator path is now real: standard-library Inspect, locked
Replay, twice-repeated offline setup, production frontend build, and the
same-origin Judge UI/API all passed. The doctor correctly separates the native
dashboard from its Docker delivery and returns an unsupported exit for the
latter on this host.

The final post-audit macOS rerun proved the project-local,
SHA-512-pinned Godot 4.4 runtime with a clean-worktree two-run/four-week fresh
trace. It binds the exact embedded game commit/content tree, audited runtime
overlay, and game/runtime/execution source fingerprints. The exact command set and result digests are retained in
`platform-evidence/macos-native.json`.

At the same `6fd5874d` contract, Linux amd64 native/container acceptance passed in workflow run
`29530325297`. Official Linux Godot 4.4 also passed in run `29530260522`: five
contract validators were clean, and the three declared demo balance findings
matched the exact pin-bound expected-failure contract. The generated evidence
is retained in `platform-evidence/linux-amd64.json` and
`platform-evidence/linux-godot.json`.

This is not yet a complete cross-platform pass. Docker is absent locally and no
OpenAI key is configured. Docker evidence is therefore assigned to the proven
Linux amd64 CI path. Linux arm64 and the published multi-architecture registry
manifest remain release gates rather than tested claims; the live OpenAI path
also remains unproven.

Machine-readable details and remediation are in
`P4-platform-delivery.review.json`. G4 remains open until arm64, registry, and
the separately authorized live OpenAI evidence are replaced by dated run
records rather than source inspection.
