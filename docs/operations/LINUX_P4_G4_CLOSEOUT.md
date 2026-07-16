# Linux P4/G4 closeout

This runbook closes only evidence that was actually executed. Source inspection,
emulation, a feature-branch push without a PR, and a DeepSeek-compatible smoke
must not be recorded as passing Linux or OpenAI evidence.

## 1. Freeze the delivery revision

Use the exact revision that will be judged and keep its worktree clean:

```bash
git status --short
git rev-parse HEAD
./judge --mode inspect --offline --json --output-dir -
./judge --mode replay --offline --json --output-dir -
```

The `Test` workflow runs for pull requests, pushes to `main`, scheduled runs,
or manual dispatch. A feature-branch push by itself does not trigger it.

On Apple Silicon, refresh all native macOS rows with one clean-worktree run:

```bash
scripts/run-p4-macos
uv run python tools/record_platform_evidence.py \
  --mode macos \
  --artifact-dir reports/platform-acceptance/macos-native \
  --output docs/reviews/openai_build_week_2026/platform-evidence/macos-native.json \
  --update-review
```

The recorder rejects stale doctor/Godot outputs, a dirty source revision,
non-arm64 macOS, the wrong Godot version, or a missing native UI/API response.

## 2. Native Linux amd64 and hardened Docker

On a native Linux x86_64 host with Docker Engine:

```bash
scripts/run-p4-linux-amd64
```

This repeats locked setup, native Inspect/Replay/UI preflights, builds the CPU
Judge image, runs Inspect and Replay without network in a read-only container,
smokes the same-origin UI/API, and writes a validated evidence JSON.

The equivalent GitHub-hosted path is the `judge-linux-amd64` job. Open a PR or
manually dispatch the workflow, retain its URL, download
`judge-linux-amd64-<run-id>`, then run this from the same tested revision:

```bash
uv run python tools/record_platform_evidence.py \
  --mode linux-amd64 \
  --artifact-dir /path/to/downloaded/reports/platform-ci \
  --output docs/reviews/openai_build_week_2026/platform-evidence/linux-amd64.json \
  --update-review
```

## 3. Pinned Linux Godot 4.4

The default workflow input is `4.4-stable`. Configure
`STUDY_IN_GERMANY_TOKEN`, manually dispatch `Test`, retain the
`game-contract-<run-id>` artifact and URL, then validate it:

```bash
uv run python tools/record_platform_evidence.py \
  --mode linux-godot \
  --artifact-dir /path/to/downloaded/game-contract \
  --output docs/reviews/openai_build_week_2026/platform-evidence/linux-godot.json \
  --update-review
```

For a local native Linux checkout, use the checksum-pinned toolchain and
canonical game materializer:

```bash
export GAME_SOURCE_PATH=/path/to/study-in-germany
scripts/run-p4-linux-godot
```

The recorder rejects non-Linux reports, dirty source, a different agent
revision, missing raw trace, an unpinned game, or Godot other than 4.4.

## 4. Publish and execute the arm64 image

The preferred evidence path is a manual `Test` workflow dispatch with
`publish_judge_image=true`. It publishes the multi-architecture image to GHCR,
then executes the digest-pinned arm64 image on GitHub's native
`ubuntu-24.04-arm` runner. Download both the image-metadata and
`judge-linux-arm64-<run-id>` artifacts before importing them into the review.

The equivalent local/registry procedure is below.

Authenticate to the registry and publish both native manifests:

```bash
export JUDGE_IMAGE_REF=ghcr.io/OWNER/playtest-forge-judge
export JUDGE_IMAGE_TAG=build-week-2026
tools/build_judge_image.sh
```

Commit the generated `judge-image-metadata.json`. It contains the registry
index digest and source-contract fingerprint; G4 rejects metadata built from
different delivery code.

On a native Linux arm64 runner:

```bash
export JUDGE_IMAGE_DIGEST_REF='ghcr.io/OWNER/playtest-forge-judge@sha256:...'
scripts/run-p4-linux-arm64-image
```

Copy the generated evidence into
`docs/reviews/openai_build_week_2026/platform-evidence/linux-arm64.json`, then
rerun the recorder with `--update-review` if the first output was under
`reports/`.

## 5. Live provider evidence

DeepSeek may be used as a provider-compatibility development smoke, but it
cannot close `live_openai_campaign`. The release row requires a completed
OpenAI Responses API campaign with response IDs, model and aggregate usage.

On macOS or Linux with the pinned game and Godot runtime:

```bash
. .tools/build-week/env.sh
export GAME_PROJECT_PATH="$PWD/reports/build-week-2026/game-source"
export OPENAI_API_KEY=... # server process only
scripts/run-p4-live-openai
```

The script runs one persona, one seed and two weeks. It stores no prompt/model
output in the committed platform evidence and rejects keys or incomplete calls.

## 6. Import and close G4

Each external evidence file must have the current
`source_contract_sha256`. After importing all rows:

```bash
uv run python tools/review_build_week_g4.py --json
git diff -- docs/reviews/openai_build_week_2026 judge-image-metadata.json
```

G4 may pass only when macOS native/Godot, Linux amd64/container/Godot, native
Linux arm64, live OpenAI, and the published two-platform image are all proven.
Do not start final P5 release claims while the command exits non-zero.
