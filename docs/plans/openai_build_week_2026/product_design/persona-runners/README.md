# Strategy Persona runner assets

This folder documents the six production runner cutouts used by the Build Week
Playthrough Inspector. The visual source is the approved roster in
`review-lab/assets/persona-roster-v2.png`; the route and all displayed values
come from committed real-Godot replay evidence rather than the illustration.

## Production assets

| Strategy | Frame A | Frame B | Route evidence |
| --- | --- | --- | --- |
| Newbie | `persona-newbie-runner-v1.png` | `persona-newbie-runner-frame-b-v1.png` | `cells/newbie-seed-42.json` |
| Study | `persona-study-runner-v1.png` | `persona-study-runner-frame-b-v2.png` | `cells/study-seed-42.json` |
| Money | `persona-money-runner-v1.png` | `persona-money-runner-frame-b-v1.png` | `cells/money-seed-42.json` |
| Social | `persona-social-runner-v1.png` | `persona-social-runner-frame-b-v2.png` | `cells/social-seed-42.json` |
| Visa | `persona-visa-runner-v1.png` | `persona-visa-runner-frame-b-v1.png` | `cells/visa-seed-42.json` |
| Slacker | `persona-slacker-runner-v1.png` | `persona-slacker-runner-frame-b-v2.png` | `cells/slacker-seed-42.json` |

All runner files are under `frontend/src/assets/competition/personas/`. All
route files are under `examples/build_week_2026/playthrough-v1/cells/`. Each
selected strategy uses its corresponding 19-node, 18-edge seed-42 cell.

## Image-generation brief

The built-in image generator produced two full-body poses per strategy, using
the approved character as the identity reference and a solid chroma background
for deterministic post-processing. Frame B changes the leading leg and adds one
strategy-specific secondary motion:

- Newbie: cautious forward step, teal jacket, backpack and notes.
- Study: brisk study-focused step, navy uniform, glasses and one book.
- Money: confident work-focused step, green jacket and coin motif.
- Social: energetic running pose, orange jacket and friendly wave.
- Visa: composed administrative stride, teal blazer, glasses, exactly two
  hands, checklist only, no DOCS folder and no extra arm.
- Slacker: sleepy standing shuffle, purple hoodie, controller held in exactly
  two hands, no chair.

The corrected v2 Study, Social, and Slacker Frame B assets explicitly swap the
leading leg while preserving identity, props, costume, and hand count. Study's
books lift slightly, Social's free arm swings, and Slacker's shoulders/controller
shift with a low-energy step.

The chroma images were keyed to alpha with a soft matte and color de-spill, then
normalized in the fixed route slot with `object-fit: contain`. Final files were
visually inspected for transparent backgrounds, clean silhouettes, correct hand
count, consistent identity, and readable scale in the route slot.

## Interaction contract

Selecting a Persona updates the query string (`?persona=<slug>`) and resets the
playhead to W1. The runner, route, week record, selected choices, evidence
console, row hashes, and provenance all change to that Persona's verified cell.

The replay week is the animation timeline; there is no independent sprite
timer. Odd weeks use Frame A and even weeks use Frame B (`W1=A`, `W2=B`,
`W3=A`, and so on). Next, Previous, node selection, keyboard navigation, and
Play therefore resolve to the same deterministic frame for a given week.
Previous never mirrors the character: it moves the runner to the prior node and
restores that week's frame while the character keeps facing the original
direction. Play advances one verified week every 850 ms, so the two poses
naturally alternate as the runner moves along the route.

Hover or keyboard focus on the route runner opens a current-state HUD containing
money, energy, stress, hunger, arrears, and cash-shortfall count from the active
node's `state_after`. It does not show before/after arrows; changes remain in the
week record below the route.

## Visual QA

- `frontend/qa-persona-switcher-visa.png`: six cutouts in the strategy switcher
  and Visa positioned on its W1 route.
- `frontend/qa-persona-runner-tooltip-visa-w1.png`: Visa current-state HUD.
- `frontend/qa-persona-runner-tooltip-social-w3.png`: Social runner, W3
  attractor, current-state HUD, and matching actual route signal.

The implementation passed 18 frontend tests, the production build, browser
interaction checks, and a clean browser-console review.
