# OpenAI Build Week 2026 submission compliance audit

Date: 2026-07-17  
Scope: repository, evaluator delivery, README, Devpost handoff  
Truth rule: an unchecked row is a release blocker, not an implied pass.

## Official requirements used

The controlling sources are the [OpenAI Build Week Devpost rules](https://openai.devpost.com/rules)
and the [OpenAI Build Week event page](https://openai.com/build-week/). The submission deadline is
July 21, 2026 at 5:00 PM PDT. The project is entered as a developer tool and must demonstrate a
coherent, runnable implementation built with Codex and GPT-5.6, distinguish prior work from new
Build Week work, and give judges free access to the submitted result.

The rules additionally require a public YouTube demo under three minutes with audio, repository
access for the judging accounts when the repository is private, setup and supported-platform
instructions, and a no-rebuild evaluation route. The README/submission must explain how Codex and
GPT-5.6 contributed, where Codex accelerated the work, and which decisions remained human-owned.

## Delivery decision

The final form is intentionally three-tiered:

1. GitHub Pages is the zero-install, no-rebuild visual story.
2. The immutable Judge image and repository `./judge` commands are the automated evaluator path.
3. Host Codex plus the `playtest-forge` Skill orchestrates authoring; Docker supplies optional Godot
   and vLLM sidecars. Codex does not run inside the Judge image and no Docker socket is mounted into
   the agent container.

The complete local/OpenAI campaign path is therefore hybrid, not an all-in-one container. Codex
runs repository commands on the host; `scripts/godot-docker-wrapper` reaches the Godot sidecar with
`docker compose exec` and falls back to one-shot `docker run`. Local vLLM is reached through its
published OpenAI-compatible endpoint. MCP is not required for this delivery path.

## Compliance ledger

| Requirement | State | Repository evidence / remaining action |
|---|---|---|
| Builds and runs consistently | Pass | Current Python/frontend suites, production frontend build, and Judge Inspect/Replay are rerun before branch publication; dated results are reported in the final handoff. |
| No-rebuild judge path | Pass | `./judge --mode inspect --offline` and `./judge --mode replay --offline`; GitHub Pages is static. |
| Supported platforms documented | Pass after this audit | Linux amd64/arm64 and macOS native evidence exists; live Godot/vLLM requirements are separated from Judge requirements. |
| Codex use documented | Pass after this audit | Repository Skill, frozen repair plans, bounded patches, evidence gates, and human decision boundary are documented. |
| GPT-5.6 use demonstrated | Pass (2026-07-18) | A sanitized, hash-verified `gpt-5.6-luna` campaign retains six personas, seed 42, 114 gameplay records, and zero fallback/provider errors. |
| Prior work distinguished | Pass | `submission/build-week-2026/PRIOR_VS_BUILD_WEEK.md`. |
| Public/private repository access | Owner action | If private, share with `testing@devpost.com` and `build-week-event@openai.com` before the deadline. |
| Team invitations accepted | Owner action | Verify every Devpost invite is accepted before the deadline. |
| Public demo video under 3 minutes | Blocked | Record, upload publicly to YouTube, verify signed-out playback, duration, audio, and captions. |
| Primary `/feedback` session ID | Owner action | Confirm the chosen primary build-thread ID in Devpost; `/feedback/` exports remain untracked and private. |
| License and attribution | Pass | MIT `LICENSE` and `ATTRIBUTION.md`. |
| Free judge access | In progress | Pages and offline Judge are unrestricted; verify final repository/image visibility. |
| English submission materials | Pass | Primary README, evaluator UI, Devpost draft, and judge docs are English. |

## README audit result

The README already has repository-only Inspect/Replay commands, the public demo URL, environment
tiers, Skill discovery, license/attribution, and prior-versus-new disclosure. This audit corrects
the stale artifact count and obsolete Docker/license limitations, and adds an explicit supported
platform/delivery matrix plus a focused Codex/GPT-5.6/human-decision explanation.

On 2026-07-18 the current local image
`playtest-forge-judge:submission-current` passed no-network, read-only,
drop-all-capabilities Inspect and Replay. Its read-only Dashboard/API returned
the signed proof, live OpenAI campaign-only record, and deterministic
correctness proof. This is local linux/amd64 evidence, not a published
current-revision multi-architecture
digest; the older GHCR digest is retained only as historical evidence.

On 2026-07-18 the redacted live bundle passed provider, provenance, schema,
hash, and privacy gates and was imported as
`examples/build_week_2026/experiments/openai-all-six-seed-42-20w`. The static
Judge truthfully labels it OPENAI API / CAMPAIGN ONLY. Local evidence is not
relabeled as OpenAI evidence, prerecorded Replay is not relabeled as an LLM run,
and the live campaign is not relabeled as repair proof.

## Final release blockers

- Complete the manual-versus-Forge comparison and non-builder clean-room evaluation.
- Record and validate the public YouTube demo.
- Confirm the primary Codex `/feedback` session ID in the Devpost form without
  publishing the private `/feedback/` export.
- Verify Devpost team invitations and repository access for both judging accounts.
- Run the final G4/G5 gates without weakening their required checks.
