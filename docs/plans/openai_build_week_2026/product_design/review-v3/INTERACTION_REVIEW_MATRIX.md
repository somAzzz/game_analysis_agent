# Interaction review matrix — Judge Mission + Playthrough Inspector

Status: `copy-and-data-locked · offline-review-pack-ready · awaiting-review-channel-decision`

This is the source of truth for the third design review. It separates the
interaction states that were compressed into the option-1 overview and binds
every playthrough claim to retained evidence. The review can be conducted in
Figma, from the checked-in PNG/PPTX pack, or through the explicitly approved
Review Lab replacement. None of those review artifacts authorizes production
frontend implementation.

## Visual source

Match the selected option-1 boards and the existing Judge Mode source tokens:

| Role | Source value |
| --- | --- |
| Background | `--judge-bg: #071318` |
| Panel | `--judge-panel: #0c1d23` |
| Primary text | `--judge-ink: #edf7f3` |
| Muted text | `--judge-muted: #9bb0af` |
| Rule | `--judge-rule: #294249` |
| Selected / observed | `--judge-cyan: #77ddd4` |
| Legal but unexecuted | `--judge-amber: #f2c66d` |
| Failure / warning | `--judge-red: #ff665f` |
| Display face | `Fraunces` |
| Body face | `Newsreader` |
| Evidence / controls | `IBM Plex Mono` |

Do not substitute Material 3 or Simple Design System styling. Those libraries
are subscribed to the Figma file, but their token model and visual language do
not match the checked-in Judge Mode.

## State matrix

### S1 — Judge Mission / default

Purpose: establish the competition thesis in under ten seconds.

- Verdict: `REJECTED`.
- Evidence summary: `18/18 cells · 342 weeks · 324 actual edges`.
- Squad: six human strategy Personas; no Codex or robot mascot.
- Primary action: `PLAY SIGNED REPLAY`.
- Truth label: `PRERECORDED · REAL GODOT 4.4 EXECUTION · HASH VERIFIED`.

Reviewer question: is it immediately clear that a passed focused test was not
enough to accept the repair?

### S2 — Persona / hover summary

Purpose: explain the selected strategy without obscuring the mission verdict.

The card must show:

1. strategy intent and priorities from the frozen Persona contract;
2. risk tolerance and exploration parameters, labelled `contract`;
3. observed action-tag rates across three seeds, labelled `observed`;
4. first cashflow-stress attractor weeks;
5. observed final-ending distribution;
6. an intent-versus-observed mismatch flag when applicable.

Do not label these as innate abilities or subjective character scores. For
example, use `study-tag share 63.2%`, not `learning ability 63`.

### S3 — Persona / click detail

Purpose: turn the Q-style person into an auditable strategy record.

Sections:

- `STRATEGY CONTRACT` — description, priorities, hard avoids, acceptable costs;
- `OBSERVED BEHAVIOR` — action-tag distribution and three-seed consistency;
- `OUTCOME` — first-attractor weeks and ending distribution;
- `EVIDENCE` — cell IDs, seeds, source rows, and row hashes;
- `LIMITATION` — Replay proves reproducibility, not a fresh model call.

The panel must preserve graph context and allow Escape, close-button, and
focus-return behavior.

### S4 — Playthrough Inspector / W1

Purpose: teach the graph grammar using an actual starting state.

Cell: `money · seed 42`.

- Selected actions: `problem_set`, `library_day`,
  `language_school_germany`, `language_tandem`.
- Event: `arrival`.
- Selected choice: `立刻去超市和 dm 补生活用品`.
- State result: money `500 → 142`, energy `100 → 48`, stress `20 → 32`.
- Four legal event choices are available at W1; only the selected choice has an
  observed result.
- Evidence: source line `1`, row SHA-256 prefix `4d66dd4714fe`.

### S5 — Playthrough Inspector / W3 first attractor

Purpose: reveal the shared failure mechanism, not merely a bad ending.

- Attractor entered: `cashflow-stress-attractor`.
- Event: `missing_school_registration`.
- Selected choice: `先找 International Office`.
- State result: stress `49 → 82`, hunger `39 → 73`, arrears `373 → 628`,
  cash-shortfall count `2 → 3`.
- Three legal event choices are displayed as short dotted stubs.
- Evidence: source line `3`, row SHA-256 prefix `4041083497b4`.

### S6 — Playthrough Inspector / W19 ending

Purpose: close the causal story and return the judge to the mission verdict.

- Event: `after_exam_void`.
- Selected choice: `稳妥处理`.
- Final state includes money `0`, hunger `100`, stress `96`, arrears `3862`,
  cash-shortfall count `16`.
- Observed ending: `cashflow_collapse`.
- Evidence: source line `19`, row SHA-256 prefix `e0458a9d636e`.
- Primary action: `RETURN TO JUDGE MISSION`.

## Six-Persona hover copy

All rates below are observed across 57 weeks and three completed cells per
Persona. Percentages are presentation rounding of the retained JSON values.

| Persona | Intent | Risk / explore | Observed action-tag highlights | First attractor weeks | Ending |
| --- | --- | --- | --- | --- | --- |
| Newbie | Follow visible guidance and avoid immediate crisis | 0.35 / 0.45 | study 57.0%, language 43.0%, social 23.7% | 6 / 6 / 14 | collapse 3/3 |
| Study | Academic progress, exams, language, APS | 0.40 / 0.25 | study 50.0%, language 50.0%, exam 25.0% | 3 / 6 / 6 | collapse 3/3 |
| Money | Money, career progress, survival | 0.65 / 0.35 | study 63.2%, language 36.8%, career 0.4% | 3 / 3 / 6 | collapse 3/3 |
| Social | Social ties, loneliness reduction, language | 0.45 / 0.55 | social 25.0%, language 50.0%, study 50.0% | 3 / 6 / 6 | collapse 3/3 |
| Visa | Visa progress, registration, deadlines, documents | 0.25 / 0.20 | admin 25.0%, study 57.0%, language 43.0% | 6 / 6 / 10 | collapse 3/3 |
| Slacker | Stress reduction, energy recovery, short-term comfort | 0.80 / 0.65 | study 62.7%, language 37.3%, social 25.0% | 3 / 6 / 6 | collapse 3/3 |

The Money card should lead the demo because its stated income/career strategy
produced only a `0.4%` observed career-tag rate and still reached the attractor
at weeks `3 / 3 / 6`. This is evidence of a strategy-to-affordance mismatch,
not a claim about the Persona's intelligence.

## Graph semantics

| Visual | Meaning | Allowed interaction |
| --- | --- | --- |
| Solid cyan edge | Observed state transition | Scrub, previous, next, play |
| Filled cyan node | Current observed week | Open synchronized evidence |
| Dotted amber stub | Legal action or choice at this observed state | Hover for requirements and known immediate effects |
| Coral ring | Failure, anomaly, or selected terminal state | Open failure evidence |
| Hidden future | No executed evidence | Never draw a projected state or ending |

`available_action_ids` and unselected `legal_choices` are choice affordances,
not alternate playthroughs. The UI must not continue their stubs into invented
nodes.

## Motion proposal for review

The corresponding character keyframes are shown in
[`PERSONA_MOTION_STORYBOARD_REVIEW.md`](PERSONA_MOTION_STORYBOARD_REVIEW.md).
The storyboard supplies character motion only; the graph remains driven by the
verified selected-cell JSON.

| Motion | Default | Reduced motion |
| --- | --- | --- |
| Persona hover card | 120 ms opacity + 4 px lift | opacity only |
| Persona selection | 180 ms outline / platform lock | immediate outline |
| One graph step | 280 ms position interpolation | immediate position change |
| Active-node pulse | 1,200 ms, maximum two cycles | static ring |
| Detail panel | 180 ms slide and fade | immediate open |
| Log-row update | 120 ms highlight | static color change |

Playback must move the Persona, graph focus, state delta, event card, and log
selection in one transaction. Motion may clarify state change but cannot be the
only indication of selection or failure.

## Ninety-second judge route

| Time | State | Judge narration target |
| --- | --- | --- |
| 0–10 s | S1 | “The patch passed its focused test. We rejected it.” |
| 10–22 s | S2 Money hover | Strategy intent versus observed action mix |
| 22–34 s | S3 Money detail | Three seeds, evidence citations, Replay truth label |
| 34–48 s | S4 W1 | Actual state, selected actions, legal-option grammar |
| 48–65 s | S5 W3 | First attractor and synchronized evidence |
| 65–80 s | S6 W19 | Collapse ending and cumulative state pressure |
| 80–90 s | S1 return | Rejected repair and Playtest Forge value proposition |

## Approval decisions

- [ ] S1 verdict hierarchy and primary action;
- [ ] S2 hover field names and observed/contract distinction;
- [ ] S3 detail information architecture;
- [ ] S4/S5/S6 graph and evidence synchronization;
- [ ] Money as the default demo Persona;
- [ ] solid-path / dotted-stub / hidden-future grammar;
- [ ] motion timings and reduced-motion behavior;
- [ ] keyboard, focus-return, contrast, target size, and log semantics.

## Review delivery status

The offline review pack is complete:

- [`option-1-figma-import-review-v3.pptx`](option-1-figma-import-review-v3.pptx);
- [`figma-import/01-evidence-overview.png`](figma-import/01-evidence-overview.png);
- [`figma-import/02-interaction-states.png`](figma-import/02-interaction-states.png);
- [`figma-import/03-persona-motion.png`](figma-import/03-persona-motion.png).

All three boards were rendered at 1536×1024, inspected individually, rendered
again from the exported PowerPoint, and passed the presentation overflow test.
They are sufficient for an asynchronous annotated review without Figma.

If interaction behavior must be reviewed directly, use the bounded replacement
defined in [`REVIEW_LAB_PROPOSAL.md`](REVIEW_LAB_PROPOSAL.md). Do not turn that
prototype into a production route before the approval checklist above is
signed off.

### Figma write status

The target remains
[the option-1 Figma file](https://www.figma.com/design/9Gxo5Rbvo1UHyN7wMAg30d).
The intended `03 — Interaction + Evidence Review Matrix` creation was rejected
atomically by the Figma Starter MCP call limit on 2026-07-17; no partial nodes
were created. Resume the write only after capacity returns, then validate the
new frame with metadata and a full-resolution screenshot.
