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
| Builds and runs consistently | Pass | Python (494 passed, 1 environment skip), frontend (25 passed), Judge Inspect/Replay, and the final local A/B image all pass. |
| No-rebuild judge path | Pass | `./judge --mode inspect --offline` and `./judge --mode replay --offline`; GitHub Pages is static. |
| Supported platforms documented | Pass after this audit | Linux amd64/arm64 and macOS native evidence exists; live Godot/vLLM requirements are separated from Judge requirements. |
| Codex use documented | Pass after this audit | Repository Skill, frozen repair plans, bounded patches, evidence gates, and human decision boundary are documented. |
| GPT-5.6 use demonstrated | Blocked | Adapter and server-side key boundary exist, but the release still needs one retained, redacted, bounded GPT-5.6 campaign. |
| Prior work distinguished | Pass | `submission/build-week-2026/PRIOR_VS_BUILD_WEEK.md`. |
| Public/private repository access | Owner action | If private, share with `testing@devpost.com` and `build-week-event@openai.com` before the deadline. |
| Team invitations accepted | Owner action | Verify every Devpost invite is accepted before the deadline. |
| Public demo video under 3 minutes | Blocked | Record, upload publicly to YouTube, verify signed-out playback, duration, audio, and captions. |
| Primary `/feedback` session ID | Owner action | Retrieve from the primary build thread and place it in final submission metadata. |
| License and attribution | Pass | MIT `LICENSE` and `ATTRIBUTION.md`. |
| Free judge access | In progress | Pages and offline Judge are unrestricted; verify final repository/image visibility. |
| English submission materials | Pass | Primary README, evaluator UI, Devpost draft, and judge docs are English. |

## README audit result

The README already has repository-only Inspect/Replay commands, the public demo URL, environment
tiers, Skill discovery, license/attribution, and prior-versus-new disclosure. This audit corrects
the stale artifact count and obsolete Docker/license limitations, and adds an explicit supported
platform/delivery matrix plus a focused Codex/GPT-5.6/human-decision explanation.

The final local image `playtest-forge-judge:ab-final` passed read-only, no-network
Inspect and Replay; Inspect verified 599 signed files. Its read-only, dropped-capability
Dashboard/API exposed signed Replay and both local A/B proof-complete experiments.
The image is local evidence, not a published multi-architecture digest.

The README must not say that a live GPT-5.6 experiment exists until the redacted bundle passes the
same provider, provenance, and privacy gates as local vLLM. Local evidence cannot be relabeled as
OpenAI evidence, and prerecorded Replay cannot be relabeled as an LLM run.

## Final release blockers

- Retain one bounded GPT-5.6 campaign and update the claim ledger truthfully.
- Complete the manual-versus-Forge comparison and non-builder clean-room evaluation.
- Record and validate the public YouTube demo.
- Retrieve the primary Codex `/feedback` session ID.
- Verify Devpost team invitations and repository access for both judging accounts.
- Run the final G4/G5 gates without weakening their required checks.
