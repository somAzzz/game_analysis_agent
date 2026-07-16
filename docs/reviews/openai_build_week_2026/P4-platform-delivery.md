# P4 platform delivery review

Status: **partial**

Date: 2026-07-16

Machine: macOS 26.5.2, Apple Silicon arm64

Reviewed source: `5b0cce6d384e269f06c71e10f6e184b7709b0aa8`

Delivery contract: `519926eff940f5c360bef72d786b3afd48f2407c10b811c75c8058e9ed5c1970`

The macOS-native evaluator path is now real: standard-library Inspect, locked
Replay, twice-repeated offline setup, production frontend build, and the
same-origin Judge UI/API all passed. The doctor correctly separates the native
dashboard from its Docker delivery and returns an unsupported exit for the
latter on this host.

The post-audit macOS rerun proved the project-local,
SHA-512-pinned Godot 4.4 runtime with a clean-worktree two-run/four-week fresh
trace. It binds the exact embedded game commit/content tree, audited runtime
overlay, and game/runtime/execution source fingerprints. The exact command set and result digests are retained in
`platform-evidence/macos-native.json`.

After the final expected-failure gate changed the delivery contract, those
macOS rows became stale and are queued for one last native rerun. At contract
`6fd5874d`, Linux amd64 native/container acceptance passed in workflow run
`29530325297`. Official Linux Godot 4.4 also passed in run `29530260522`: five
contract validators were clean, and the three declared demo balance findings
matched the exact pin-bound expected-failure contract. The generated evidence
is retained in `platform-evidence/linux-amd64.json` and
`platform-evidence/linux-godot.json`.

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
