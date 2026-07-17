# Review Lab proposal — interaction review without Figma

Status: `recommended · not-yet-authorized-for-implementation`

## Recommendation

Use an isolated browser Review Lab as the primary interaction-review surface if
the team decides not to wait for Figma. A browser prototype is better suited to
reviewing Persona hover/click states, synchronized graph playback, logs, and
reduced-motion behavior than a static canvas.

The Review Lab is not the final competition frontend. It must live outside the
product router, consume read-only retained evidence, and remain removable. Its
components may be migrated only after the review checklist is approved.

## Required review surfaces

### Judge Mission

- Six human strategy Personas: Newbie, Study, Money, Social, Visa, and Slacker.
- Hover reveals contract intent, risk/exploration inputs, observed action-tag
  rates, first-attractor weeks, and ending distribution.
- Click opens the strategy contract, observed behavior, outcome, evidence, and
  limitation sections.
- Money is the default demonstration Persona because its income/career contract
  produced only a 0.4386% observed career-tag rate and collapsed in all seeds.

### Playthrough Inspector

- Load the retained `money · seed 42` playthrough view directly.
- Support Previous, Next, Play/Pause, explicit W1/W3/W19 jumps, keyboard input,
  and reduced motion.
- Move the selected Persona only across recorded edges.
- Synchronize active node, state delta, action/event/choice content, selected
  log row, source line, and row hash in one state transaction.
- Render unselected legal choices only as short dotted affordance stubs. Never
  invent a future node, route, state, or ending.

### Reviewer controls

- Direct state selector for S1–S6.
- Optional annotation overlay with numbered review callouts.
- Toggle for evidence emphasis, motion on/off, and projector-safe contrast.
- Deterministic reset to the approved 90-second judge route.

## Data contract

The prototype may read only the generated views under
`examples/build_week_2026/playthrough-v1/`. The corresponding verifier must pass
before every published capture:

```bash
uv run python tools/verify_playthrough_views.py
```

Required truth label: `prerecorded-real-godot-replay`. The UI must state that
Replay proves reproducibility and does not represent a fresh OpenAI call.

## Proposed repository boundary

```text
docs/plans/openai_build_week_2026/product_design/review-lab/
├── prototype/        # isolated static browser prototype
├── screenshots/      # annotated review captures
├── recordings/       # deterministic interaction clips
├── evidence/         # generated read-only evidence mapping
└── REVIEW_GUIDE.md   # S1–S6 review and approval checklist
```

Do not add the Review Lab to the existing application navigation, backend API,
or deployment pipeline before design approval.

## Review acceptance gate

- [ ] Judge verdict hierarchy and primary action are understandable in ten seconds.
- [ ] Contract values and observed metrics cannot be confused.
- [ ] Persona hover, click detail, keyboard, and focus return are approved.
- [ ] W1/W3/W19 playback matches the retained cell exactly.
- [ ] Solid path, dotted legal stub, hidden future, and terminal-risk semantics are approved.
- [ ] Logs and hashes remain readable at the presentation viewport.
- [ ] Motion and reduced-motion behavior communicate the same state.
- [ ] The team explicitly authorizes migration into production pages.

## Decision required

Choose one interaction-review channel before implementation:

1. wait for Figma write capacity and complete the original v3 canvas; or
2. authorize the isolated Review Lab as the Figma replacement.

The checked-in PNG/PPTX pack supports either decision and does not need to be
redesigned.
