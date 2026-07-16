# Playtest Forge Judge Guide

## Run these first

From a repository checkout:

```bash
./judge --mode inspect --offline --json --output-dir -
./judge --mode replay --offline --json --output-dir -
```

For an idempotent source setup including the UI, run
`scripts/setup-evaluator`. Set `EVALUATOR_OFFLINE=1` to require dependency
caches and prohibit package downloads. The setup is non-root, uses both
lockfiles, regenerates the public fixture, builds the UI, and runs both Judge
checks.

Preflight one intended mode without exposing secrets:

```bash
/usr/bin/python3 tools/judge_doctor.py --mode inspect --json
uv run python tools/judge_doctor.py --mode dashboard-native --json
uv run python tools/judge_doctor.py --mode dashboard-container --json
```

The doctor distinguishes native and container dashboards and returns exit 10
for a missing required capability. Optional missing tools are warnings.

## Tested-platform ledger

| Delivery path | Dated result | Claim level |
| --- | --- | --- |
| macOS 26.5.2 arm64, native Inspect/Replay/UI | Passed 2026-07-16 | Verified locally |
| macOS arm64, Docker dashboard/Replay | Optional; Docker absent | Not required for release |
| macOS arm64, fresh pinned Godot 4.4 | Passed 2026-07-16 | Verified locally |
| Linux amd64 native/container | Workflow implemented, execution pending | Target only until CI artifact exists |
| Linux amd64, fresh pinned Godot 4.4 | Manual/scheduled workflow implemented, execution pending | Target only until CI artifact exists |
| Linux arm64 container | Multi-arch source target, not executed | Target only |
| Live OpenAI campaign | Not run; no server key | Optional capability only |

See `docs/reviews/openai_build_week_2026/P4-platform-delivery.review.json` for
the machine-readable checks. “Target” and “workflow implemented” do not mean
tested or supported.

Expected result for both commands is a single JSON object with
`"schema_version":"judge-result-v1"` and `"status":"passed"` on stdout.
Logs and failures use stderr unless `--stdout-only` is supplied. Passing
`--output-dir -` guarantees that the evaluator writes no result file.

Inspect normally completes in under 30 seconds and Replay in under 120 seconds.
The current reference measurements are milliseconds for Inspect and below one
second for Replay on the development host; they are observations, not platform
guarantees.

## Capability labels

| Label | Meaning | Current evidence |
| --- | --- | --- |
| Prerecorded | Hash-pinned Replay decisions and committed Godot-derived rows | Default Inspect and Replay paths |
| Live | A fresh request to a model or fresh execution of the game | Not performed by the offline commands |
| Unsupported | A capability is unavailable in the current environment | Must return non-zero and must not be presented as pass |
| Failed | Inputs, hashes, schemas, claims, dependencies, timeout, or gates failed | Must return non-zero with remediation |

The offline evidence is not relabeled as live. No API key is read, accepted, or
returned by `judge`.

## What Inspect proves

Inspect is a Python-standard-library program. It reads
`judge-manifest.json`, rejects absolute/traversal paths and symlink artifacts,
then checks:

1. manifest and declared artifact schemas;
2. byte size and SHA-256 for 39 public evidence and Skill artifacts;
3. six public claims against exact RFC 6901 JSON pointers;
4. committed campaign, repair, and independent G2/G3 review evidence.

It requires Python 3.9+ only. It does not import the project package and does
not need `uv`, Docker, Godot, network, secrets, GPU, TTY, browser, port, or a
sibling `study-in-germany` checkout.

## What Replay proves

Replay uses `uv run --offline --frozen` and has a hard 120-second parent timeout
with process-group cleanup. It:

1. reparses and hash-verifies the campaign and repair bundles;
2. consumes an exact decision and event through `RecordedPersonaGateway`;
3. parses all 684 unique entries in the full fixture;
4. recomputes six-persona, validity, fallback, and selected-cluster evidence;
5. confirms designed failure remains possible and the ineffective candidate
   remains rejected.

Replay does not call OpenAI, rerun Godot, rebuild the game, or require private
assets. Its purpose is deterministic no-rebuild verification.

## Central result

The reference campaign ran 18 persona/seed cells for 342 Godot gameplay weeks.
All 18 entered the selected cashflow/stress cluster. Codex cited cross-persona
facts, froze one mechanism hypothesis, changed two allowlisted game files in an
isolated worktree, and ran fixed and holdout A/B cohorts. The patch improved
mean final cash but reduced target membership by 0% in both cohorts, so the
evidence gates rejected it and it was not merged.

This is the useful demonstrated outcome: Playtest Forge prevents a plausible,
locally tested patch from being promoted when causal and holdout evidence do not
support the intended fix. It is not a claim that this candidate repaired the
game.

Evidence entrypoints:

- `judge-manifest.json`: machine-readable table of contents and claims.
- `examples/build_week_2026/campaign-v1/`: sanitized campaign bundle.
- `examples/build_week_2026/experiment-v1/`: four-cohort repair bundle and patch.
- `docs/reviews/openai_build_week_2026/G2-campaign.review.json`: independent campaign review.
- `docs/reviews/openai_build_week_2026/G3-repair.review.json`: independent causal repair review.

## Exit and result protocol

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `passed` | Every required check for the selected stage passed |
| 1 | `failed` | Evidence, dependency, timeout, or worker failure |
| 2 | n/a | Invalid command-line usage |
| 3 | `unsupported` | Reserved for an explicitly unavailable capability |

Stable result fields include `status`, `stage`, `duration_ms`, `checks`,
`artifacts`, `limitations`, `error_code`, `error`, and `remediation`.

To retain a result atomically instead of stdout-only output:

```bash
./judge --mode replay --offline --json --output-dir reports/judge
```

## Failure recovery

- `artifact_integrity_failed`: restore the named artifact from the reviewed
  commit; do not trust the bundle currently on disk.
- `claim_value_mismatch`: the public claim and evidence disagree; correct and
  review them together.
- `dependency_missing`: install `uv`, or use dependency-free Inspect.
- `replay_worker_failed`: run `uv sync --frozen`, then retry offline Replay.
- `replay_timeout`: inspect the committed evidence, then diagnose the locked
  environment; a timeout is not success.
- `python_unsupported`: use Python 3.9+ for Inspect; Replay continues to use
  the repository's locked Python through `uv`.

## Human Judge UI

The React root route presents the same case as a three-stage evidence ledger:
Campaign, Repair, and Proof. It explicitly labels the Godot runtime, Replay
action provider, optional OpenAI live subagent, fixed/holdout cohorts, and the
rejected candidate. The former report dashboard remains at `/reports`.

Build and start the same-origin UI/API locally:

```bash
cd frontend && npm run build:public && cd ..
uv run python tools/run_judge_api.py --host 127.0.0.1 --port 8080
```

When the API is absent, the public build loads the sanitized
`judge-demo.json` fixture and labels itself `Static evaluator copy`. It does
not enable buttons or claim a live run. Docker, live OpenAI, and fresh
real-Godot runs remain deeper optional paths; their absence must not block the
repository-only checks above.
