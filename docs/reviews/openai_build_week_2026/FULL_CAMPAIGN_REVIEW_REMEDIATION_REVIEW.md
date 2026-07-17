# Full-campaign review remediation review

Date: 2026-07-17
Plan reviewed: `docs/plans/openai_build_week_2026/FULL_CAMPAIGN_REVIEW_REMEDIATION_PLAN.md`
Status: Build Week scope implemented; large-batch parent review queue remains follow-up

## Executive result

The implementation now supports the intended Codex-first competition flow:
start one shared Judge API, run Replay, local vLLM, or OpenAI through the same
campaign service, publish live evidence incrementally, replay an exact
persona/seed path, present the newest verified campaign in Judge Mission, and
record a bounded human final decision on the same evidence.

The fixes apply to the shared execution and evidence layers. They are not
local-vLLM-only patches; OpenAI uses the same campaign service, aggregation,
publication, frontend index, and Judge experiment contracts.

## Finding disposition

| Finding | Result | Review evidence |
| --- | --- | --- |
| A-01 structured endings were unknown | fixed | terminal Godot step exposes `final_ending`; aggregation fails closed on missing endings |
| A-02 resume states were misleading | fixed | retained cells hydrate as retained; completion follows final validation |
| A-03 resumed call counts reset | fixed | retained and new provider calls are cumulative |
| A-04 Judge providers diverged | fixed | Replay, vLLM, and OpenAI are explicit providers; vLLM/OpenAI delegate to `run_persona_campaign` |
| UI-01 event language tab was unnecessary | fixed | event evidence renders English without a language tab |
| UI-02 exact persona/seed replay was unavailable | fixed | hash-bound cell index plus URL-owned persona and seed, with lazy trace loading |
| UI-03 Judge Mission stayed on Replay | fixed | Latest and Signed Replay are distinct, truth-labelled sources |
| UI-04 no human disposition | fixed | stage 04 Human Review, durable/exportable record, no auto-merge |
| UI-05 no scalable cell review index | fixed for one campaign | lightweight index and single-cell loading; cross-campaign queue remains Phase 5 |
| UI-06 completed campaigns showed 95% | fixed | validated completed terminal state renders 100% |

## Shared local/API behavior

Provider-specific code now selects credentials, endpoint, model, and provider
label. The following behavior is shared:

1. campaign request and safety bounds;
2. real-Godot weekly execution;
3. resume validation and call accounting;
4. result aggregation and terminal-ending validation;
5. incremental session publication;
6. sanitized playthrough bundle and hash-bound cell index;
7. exact persona/seed frontend retrieval;
8. Judge Mission latest/replay presentation;
9. experiment fingerprint and Human Review contract.

Replay remains explicitly prerecorded. vLLM and OpenAI never silently fall back
to Replay or to one another. The vLLM Judge health check must complete a
bounded generation, not only list models. OpenAI credentials remain
server-side.

## Large-batch review result

The immediate 25-seed pain point was not raw file generation; it was discovery
and selective loading. The frontend now loads a small campaign index and only
the chosen cell trace. A reviewer can deep-link a specific strategy and seed,
change either control, preserve browser history, and return to the same path.

This is sufficient for the Build Week demonstration and a campaign within the
100-cell cap. It is not a complete multi-campaign review workbench. Pagination,
reviewer assignment, issue disposition, and a parent manifest combining
multiple campaign fingerprints remain an explicit Phase 5 follow-up.

## Human Decision review

Human Decision is integrated as the fourth Judge stage, after machine Proof.
The dedicated design and interaction audit is:
[Human Decision frontend integration review](HUMAN_DECISION_FRONTEND_INTEGRATION_REVIEW.md).

The final human record is additive. It cannot rewrite machine gates, evidence,
or the patch and cannot merge code.

## Verification gates

Focused verification completed during implementation:

- Python game-tool, aggregation, campaign-service, playthrough-view, Judge API,
  and live-provider tests;
- frontend component/API/lazy-playthrough tests;
- frontend production build;
- visual desktop and 390 px mobile review;
- static and live Judge source-state coverage.

Final repository-wide lint, test, build, diff, and Docker Godot checks are run
immediately before the module commits; their exact results belong in the
commit handoff rather than being predeclared here.

## Competition alignment

The repaired flow supports the entry's strongest claim: Codex orchestrates a
bounded, auditable repair loop whose evidence remains inspectable by both
machines and people. It avoids overclaiming autonomy because provider truth
labels are explicit, failed holdout evidence stays failed, and a human decision
does not imply an automatic code merge.

## Remaining non-blocking work

- a parent manifest and review queue for multiple large campaigns;
- hosted authentication, quota, retention, and reviewer identity;
- measured accessibility/contrast audit beyond the current semantic and visual
  checks;
- live OpenAI evidence for the final model-specific competition claim;
- the existing vLLM CUDA Graph deployment follow-up.

None of these should be represented as completed Build Week evidence until the
corresponding artifacts exist.
