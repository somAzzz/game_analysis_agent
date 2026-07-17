# Product-design evidence

The full product, frontend, UI/UX, and competition-judge review is in
[`COMPETITION_PRODUCT_DESIGN_REVIEW.md`](COMPETITION_PRODUCT_DESIGN_REVIEW.md).

The implementation-ready breakdown, ownership map, dependencies, and
Definitions of Done for the two competition-critical pages are in
[`CORE_PAGE_IMPLEMENTATION_PLAN.md`](CORE_PAGE_IMPLEMENTATION_PLAN.md). Its
Playthrough contract uses the actual embedded Demo content and committed Replay
data without a game-data sanitization layer.

The completed data-readiness audit and test plan for producing truthful playthrough
nodes, edges, Persona metrics, and route views is in
[`PLAYTHROUGH_EVIDENCE_READINESS_PLAN.md`](PLAYTHROUGH_EVIDENCE_READINESS_PLAN.md).

## Option 1 review and implementation

The team approved the option-1 direction on 2026-07-17 and explicitly selected
the browser-based Review Lab instead of Figma. The Figma experiment and
[`FIGMA_REVIEW_V2_AUDIT.md`](FIGMA_REVIEW_V2_AUDIT.md) remain historical review
records only; they are not part of the current workflow.

The interaction-review board was specified in
[`review-v3/INTERACTION_REVIEW_MATRIX.md`](review-v3/INTERACTION_REVIEW_MATRIX.md),
including the six explicit UI states, actual `money · seed 42` W1/W3/W19 facts,
Persona hover metrics, motion proposal, and 90-second judging route. Those
requirements were implemented and verified in the formal frontend.

The same review is now available without Figma as an editable PowerPoint plus
three native 1536×1024 annotated boards:

- [`review-v3/option-1-figma-import-review-v3.pptx`](review-v3/option-1-figma-import-review-v3.pptx)
  — three-slide review deck for PowerPoint, Keynote, Google Slides import, or a
  later Figma upload;
- [`review-v3/figma-import/README.md`](review-v3/figma-import/README.md)
  — board inventory, hashes, evidence boundary, and visual-QA record.

The selected review surface is the isolated, data-driven browser prototype
defined in [`review-v3/REVIEW_LAB_PROPOSAL.md`](review-v3/REVIEW_LAB_PROPOSAL.md).
It remains an editable reference, while the approved direction has now been
migrated into the product frontend:

- [`JudgeMissionExperience.tsx`](../../../../frontend/src/components/competition/JudgeMissionExperience.tsx)
  — six-Persona hover/focus summaries, detail drawer, actual campaign facts,
  representative route, and Inspector handoff;
- [`PlaythroughInspectorPage.tsx`](../../../../frontend/src/pages/PlaythroughInspectorPage.tsx)
  — six actual Persona `seed 42` paths, strategy-aware character switching,
  playback, keyboard controls, current-state runner HUD, synchronized step
  inspector, state delta, and signed evidence console;
- [`frontend/design-qa.md`](../../../../frontend/design-qa.md) — source-versus-
  implementation comparison, responsive review, interaction regression, and
  final QA result.

The production-ready transparent runner set, Persona-to-route mapping, image
generation brief, alpha-cutout method, and QA captures are documented in
[`persona-runners/README.md`](persona-runners/README.md).

The current visual-consistency audit for Report Archive, Issue Detail, Decision
Graph, and system states is in
[`audit-auxiliary-2026-07-17/AUDIT.md`](audit-auxiliary-2026-07-17/AUDIT.md).
It recommends extracting the shared competition shell first, then migrating the
Decision Graph, Issue Detail, Report Archive, and system states in that order.

The implementation-ready all-route product specification is in
[`ui-system-v2/PRODUCT_UI_SYSTEM.md`](ui-system-v2/PRODUCT_UI_SYSTEM.md). Its
independent four-perspective review and implementation gates are in
[`ui-system-v2/DESIGN_REVIEW.md`](ui-system-v2/DESIGN_REVIEW.md).

The six-strategy motion reference and its visual QA are in
[`review-v3/PERSONA_MOTION_STORYBOARD_REVIEW.md`](review-v3/PERSONA_MOTION_STORYBOARD_REVIEW.md).
It preserves all six human Persona identities across idle, hover, selected,
move, and detail-open states while deliberately leaving evidence copy blank for
verified UI data.

- [`concepts/option-1-actual-replay-review-v2.png`](concepts/option-1-actual-replay-review-v2.png)
  — Judge Mission and Playthrough Inspector using the fresh real-Godot
  `money · seed 42` replay facts, with unexecuted choices shown as legal stubs.
- [`concepts/strategy-persona-concept-sheet.png`](concepts/strategy-persona-concept-sheet.png)
  — the six strategy Persona characters and their idle, hover, selected, walk,
  and detail-open states. No Codex or robot mascot is used.
- [`concepts/persona-motion-storyboard-v1.png`](concepts/persona-motion-storyboard-v1.png)
  — the six Persona identities moving through the Inspector interaction; its
  decorative background route is not evidence and must be replaced by the
  selected cell's verified graph data.

The concept images remain review artifacts. `PF-00`–`PF-05` pass against the
retained real-Godot evidence, the Review Lab direction is approved, and the two
competition-critical experiences are implemented in the formal frontend.

The retained frontend data source is
[`examples/build_week_2026/playthrough-v1/`](../../../../examples/build_week_2026/playthrough-v1/README.md).

These screenshots record the evaluator-facing Build Week presentation at
1280×720. They are visual review evidence, not execution proof: the authoritative
claims, hashes, and platform results remain in `judge-manifest.json` and
`docs/reviews/openai_build_week_2026/`.

The captured UI deliberately identifies retained results as static or
prerecorded evidence. It must not be used to imply that a live OpenAI campaign
was run.

## Evidence set

- `evidence/01-judge-mode.jpg` — evaluator landing page and rejected decision.
- `evidence/02-campaign-stage.jpg` — campaign-stage evidence presentation.
- `evidence/03-report-archive.jpg` — retained report archive.
- `evidence/04-issue-detail.jpg` — selected issue evidence and diagnosis.
- `evidence/05-decision-graph-cover.jpg` — decision-graph entry state.
- `evidence/06-decision-graph-canvas.jpg` — decision-graph exploration state.
- `evidence/07-decision-graph-playback.jpg` — decision playback state.

These images are supporting material for product-design review and demo/video
planning. Automated reviewers should start from
`docs/plans/openai_build_week_2026/README.md` and `JUDGE.md`.
