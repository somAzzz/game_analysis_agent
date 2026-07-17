# Figma review v2 audit — Judge Mission + Playthrough Inspector

Status: `review-ready · frontend-blocked-on-design-approval`

Figma: [Evidence-driven core-page review](https://www.figma.com/design/9Gxo5Rbvo1UHyN7wMAg30d)

The locked copy, actual Money-route states, Persona metric semantics, motion
proposal, and 90-second interaction review are in
[`review-v3/INTERACTION_REVIEW_MATRIX.md`](review-v3/INTERACTION_REVIEW_MATRIX.md).

This audit covers the option-1 game-developer visual direction after replacing
the earlier mascot concept with six human strategy Personas. It is a design
review artifact, not frontend implementation approval.

## Current review canvas

![Figma review section with the two annotated boards](audit-v2/04-figma-review-section-v2.png)

The Figma section restores both imported boards to their native aspect ratios
and adds the evidence semantics and approval gate directly beneath them. The
previous 400×300 thumbnails were not readable enough for serious review.

## Evidence gate

The route visualization is no longer waiting for test data. The retained
campaign is a fresh real-Godot 4.4 execution using the hash-pinned Replay
provider:

- 18/18 campaign cells completed;
- 342 observed weekly nodes and 324 observed transitions;
- 1,336 legal choices recorded at the observed states;
- six strategy Personas, with 18 target members present;
- zero fallback or provider errors;
- all 18 observed endings are `cashflow_collapse`.

The authoritative, verifier-backed frontend views are in
[`examples/build_week_2026/playthrough-v1/`](../../../../examples/build_week_2026/playthrough-v1/README.md).
Solid route edges may represent observed transitions. Unselected legal choices
may only be short dotted stubs. They must never be extended into invented
counterfactual nodes or endings.

## Review findings

### 1. Judge Mission — strong competition entry, interaction states still need sign-off

What works:

- The rejected verdict is immediate and memorable; it tells a better judging
  story than a generic analytics dashboard.
- The six-person squad turns strategy comparison into a game-development tool
  instead of a business BI screen.
- The provenance panel and signed-replay action make the evidence trail visible
  without dominating the main narrative.

Before frontend implementation:

- Lock the hover-card fields to observed metrics and strategy intent. Do not use
  fictional ability scores.
- Confirm the click-detail information architecture: strategy summary, observed
  behavior, campaign outcome, evidence citations, and known limitations.
- Make `Play signed replay` the unambiguous next action for the 90-second judge
  path.

### 2. Playthrough Inspector — evidence-correct model, branch semantics must remain explicit

What works:

- Previous, play/pause, and next controls match the requested step-by-step agent
  inspection model.
- The selected Persona walks on the committed route while the evidence console
  exposes action, event, choice, and artifact citations.
- W1 → W3 first attractor → W19 ending creates a concise demo narrative without
  hiding the full 19-week run.

Before frontend implementation:

- Dotted option stubs need a persistent legend and hover copy saying “legal at
  this state; future not executed.”
- Path playback must update graph focus, event cards, Persona position, and log
  rows as one synchronized state.
- The separate Judge-default, Persona-hover, Persona-detail, Inspector-W1,
  Inspector-W3, and Inspector-W19 review states still need explicit approval.
  Their exact copy and evidence bindings are now locked in the v3 interaction
  matrix specification.

### 3. Six strategy Personas — distinctive and useful, metric language needs a contract

What works:

- Silhouette, color, posture, and props differentiate Newbie, Study, Money,
  Social, Visa, and Slacker without relying on a robot or Codex mascot.
- Idle, hover, selected, walk, and detail-open states are sufficient to plan the
  main interaction and motion system.

Before frontend implementation:

- Hover labels should use calculated rates such as learning-action share,
  social-action share, income-oriented action share, risk exposure, and observed
  ending—not subjective “learning 92/100” scores.
- Define timing and reduced-motion behavior: idle loop, one-node walk, selected
  pulse, and detail transition.

### 4. Accessibility and judge-room reliability — not yet proven by the mockup

- The dark teal/coral palette is visually strong, but screenshot inspection does
  not prove text and non-text contrast.
- Small monospace evidence labels must be tested at the actual presentation
  viewport, not only on the Figma canvas.
- Keyboard focus order, visible focus, 44×44 targets, log-table semantics, screen
  reader labels, and `prefers-reduced-motion` remain implementation acceptance
  tests.
- The page must remain understandable if animation is disabled or the projector
  reduces contrast.

## Recommended 90-second judge route

1. Read the rejected mission verdict and campaign evidence summary.
2. Hover Money to reveal observed strategy metrics.
3. Open Money details and select `Play signed replay`.
4. At W1, establish the starting state and available legal choices.
5. Jump to W3 and explain the first attractor using the synchronized log.
6. Jump to W19, show `cashflow_collapse`, then return to Judge Mission.

## Approval gate

Frontend work remains blocked until the review explicitly approves:

- [ ] visual direction;
- [ ] six Persona silhouettes and names;
- [ ] hover-summary fields;
- [ ] click-detail sections;
- [ ] observed-path and legal-stub semantics;
- [ ] 90-second judge route;
- [ ] motion and reduced-motion rules;
- [ ] contrast, focus, keyboard, and target-size acceptance criteria.
