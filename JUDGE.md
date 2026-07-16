# Playtest Forge Judge Guide

## Run these first

From a repository checkout:

```bash
./judge --mode inspect --offline --json --output-dir -
./judge --mode replay --offline --json --output-dir -
```

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
2. byte size and SHA-256 for 22 public artifacts;
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

Docker, browser UI, live OpenAI, and fresh real-Godot runs are deeper optional
paths. Their absence must not block these repository-only checks.
