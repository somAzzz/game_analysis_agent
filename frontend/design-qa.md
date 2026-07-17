# Option 1 competition frontend — design QA

## Comparison target

- Source visual truth: `docs/plans/openai_build_week_2026/product_design/concepts/option-1-actual-replay-review-v2.png`
- Judge Mission implementation: `frontend/qa-judge-mission-final-1536x1024.png`
- Playthrough Inspector implementation: `frontend/qa-playthrough-inspector-final-1536x1024.png`
- Persona switcher: `frontend/qa-persona-switcher-visa.png`
- Current-state HUD at W1: `frontend/qa-persona-runner-tooltip-visa-w1.png`
- Strategy/path synchronization at W3: `frontend/qa-persona-runner-tooltip-social-w3.png`
- Normalized Judge comparison: `frontend/qa-comparison-judge-final.png`
- Normalized Inspector comparison: `frontend/qa-comparison-inspector-final.png`
- Viewport: 1536 × 1024 desktop; 1024 × 768 tablet; 390 × 844 mobile
- States: Judge default + Money drawer; Inspector W1, W3, W19, playing, paused, and console-selected

The source is an annotated two-screen review montage rather than a shippable browser viewport. The normalized comparison therefore compares each source half with the matching 1536 × 1024 implementation state. The formal pages keep the source's dark evidence-ledger palette, cyan committed path, amber legal alternatives, coral rejection/terminal risk, serif verdict typography, mono evidence labels, human Persona imagery, and synchronized route/console anatomy. The formal page intentionally gives readable interactive content more vertical space than the montage.

## Full-view comparison evidence

- `qa-comparison-judge-final.png` places the normalized Judge source and browser implementation together. The verdict hierarchy, four campaign facts, selected Money Persona, hover evidence, teal/coral/amber token roles, and game-map language are preserved. The formal screen promotes the approved six-character roster above the map and continues to the actual route card on scroll.
- `qa-comparison-inspector-final.png` places the normalized Inspector source and browser implementation together. The implementation preserves the horizontal signed route, moving human Persona, W1/W3/W19 landmarks, legal-option stubs, prior/play/next controls, week record, state delta, selected choice, evidence console, and hash provenance.

## Focused-region evidence

- Persona drawer: `frontend/qa-judge-money-drawer-1536x1024.png`
- Mobile Judge: `frontend/qa-mobile-judge-390x844.png`
- Mobile Inspector: `frontend/qa-mobile-inspector-390x844.png`
- Tablet Inspector: browser checked at 1024 × 768; root width remained 1024 px and the 19-node route alone used intentional horizontal scrolling.

Focused evidence was required because the compact source montage cannot show drawer detail, keyboard focus restoration, or responsive behavior at readable scale.

## Required fidelity surfaces

### Fonts and typography

- The existing product families remain authoritative: Fraunces/Newsreader for editorial verdict and narrative copy, IBM Plex Mono for evidence, route, hashes, and controls.
- Display weight, line height, and wrapping were reduced after the first browser pass so the campaign proof and Persona system enter the desktop first viewport.
- Long event IDs and hashes wrap or truncate only in dedicated evidence regions; primary labels remain readable at desktop, tablet, and mobile widths.

### Spacing and layout rhythm

- Judge Mission uses the existing product shell and then a compact evidence strip, a roster/hover-summary pair, and the actual-route map.
- Inspector uses a heading, route, synchronized controls, week record/console pair, and provenance footer. Desktop and tablet preserve the two-column evidence relationship; mobile stacks record and console without root overflow.
- Browser measurements found `rootScrollWidth === rootClientWidth` at 1536, 1024, and 390 px. The roster and 19-node route use explicit internal overflow where the data genuinely cannot collapse further.

### Colors and visual tokens

- Existing Judge tokens are reused: `#071318` background, `#77ddd4` committed evidence, `#f2c66d` legal/unexecuted choices, `#ff665f` rejection and terminal risk.
- The generated game map uses the same cyan-left/corrupted-red-right world logic and remains low-contrast enough for route evidence.
- Focus indicators use amber and remain visible on all dark surfaces.

### Image quality and asset fidelity

- Six-Persona roster is the corrected v2 asset; Visa has exactly two arms and no DOCS folder.
- All six runners are individual transparent PNGs. Each strategy uses its own
  character in both the switcher and route; no sprite-sheet cropping or
  strategy-agnostic fallback is used.
- Visa has exactly two hands and carries only the checklist; Slacker stands and
  shuffles with the controller instead of bringing the source chair into the
  route. Chroma backgrounds and edge spill are absent in the browser captures.
- Judge route uses a project-bound generated raster map, not CSS illustration, SVG stand-in, emoji, robot, or Codex mascot.
- All UI icons use Phosphor; no text glyph substitutes are used in the new competition components.

### Copy and content

- Campaign totals, Persona contracts, observed action rates, attractor weeks, final endings, week choices, state deltas, event IDs, source lines, and row hashes come directly from `examples/build_week_2026/playthrough-v1`.
- The truth label remains `prerecorded-real-godot-replay`; copy states that Replay proves reproducibility and is not a fresh OpenAI call.
- Unselected legal choices are labeled as legal here/future not executed. No projected counterfactual state is rendered.

### Interaction and accessibility

- Persona buttons support pointer hover, keyboard focus, click-to-open, backdrop close, close button, Escape, and focus restoration.
- Inspector supports node selection, Previous/Next, W1/W3/W19 jump controls, Play/Pause, evidence-console selection, ArrowLeft/ArrowRight, and Space when focus is not on an interactive control.
- The six strategy buttons update the URL, Persona, runner, 19-node route,
  selected choices, console hashes, and provenance as one state transition.
- Hover or keyboard focus on the route runner reveals a compact current-state
  HUD for money, energy, stress, hunger, arrears, and cash shortfall. The HUD
  intentionally shows `state_after` only; before/after changes remain in the
  lower week record and live route signal.
- Route change scroll restoration was verified; entering Inspector starts at the page heading rather than inheriting Judge scroll position.
- Runner pose is deterministic by week parity (`W1=A`, `W2=B`, `W3=A`); Previous restores the prior week's pose without mirroring the character.
- Reduced-motion CSS collapses only the runner's position transition; frame selection remains synchronized with the active week.
- Browser console on a clean post-fix tab: 0 warnings, 0 errors.

## Comparison history

### Pass 1 — blocked

- [P1] Judge hero consumed the entire desktop first viewport, hiding campaign proof and Persona interaction.
  - Fix: reduced hero padding, display scale, line height, and thesis size while preserving the approved hierarchy.
  - Post-fix evidence: `frontend/qa-judge-mission-final-1536x1024.png` exposes the verdict, campaign totals, and Persona section in the first viewport.
- [P1] Hash navigation preserved the Judge scroll position when entering Inspector.
  - Fix: added route-aware scroll restoration to the application shell.
  - Post-fix evidence: browser reported `scrollY = 0` after entering Inspector; `frontend/qa-playthrough-inspector-final-1536x1024.png` starts at the route heading.
- [P2] The Money runner was half clipped at W1 because its center was positioned at 0%.
  - Fix: mapped runner motion to the same 5%–95% inset as route node centers.
  - Post-fix evidence: final desktop and mobile Inspector screenshots show the full runner at W1.
- [P2] React Router future-flag warnings polluted console verification.
  - Fix: enabled the v7 transition and relative-splat future flags on the HashRouter.
  - Post-fix evidence: clean browser tab reported 0 warning/error entries.

### Pass 2 — passed

- No actionable P0, P1, or P2 findings remain.
- Remaining P3: the competition map is a 2.6 MB PNG. It is visually sharp and does not block the judged flow; WebP/AVIF conversion can be considered after the competition review if deploy transfer size becomes important.

## Verification

- `npm run build`: passed.
- `npm test`: 18 tests passed, including Persona drawer focus restoration,
  six-strategy route switching, current-state HUD values, and
  route/record/console synchronization.
- Offline evaluator inspect/replay: passed.
- Playthrough view verifier: 18 cells, 342 nodes, 324 actual edges, truth label verified.
- Primary browser interactions: passed.
- Desktop, tablet, and mobile layout checks: passed.
- Console warning/error check: passed with zero entries on a clean tab.

core result: passed

## Auxiliary-route migration QA — 2026-07-17

### Comparison evidence

- Established visual source: `docs/plans/openai_build_week_2026/product_design/ui-system-v2/audit-before/01-judge-mission.png` and `02-playthrough-inspector.png`.
- Before migration: `audit-before/03-mission-archive-before.png` through `06-not-found-before.png`.
- After migration: `audit-after/03-mission-archive-after.png` through `06-not-found-after.png`.
- Browser comparison viewport: 1280 × 720. Source and implementation were inspected together at the same viewport.

### Pass 1 findings and fixes

- [P1 layout/color] Mission Archive filters inherited the old cream translucent surface. Fixed with a scoped Forge surface and compact evidence-cell divider.
- [P1 layout] Dossier back navigation and eyebrow collided. Fixed by making the back link and evidence eyebrow separate block rows.
- [P1 behavior] React Flow left custom nodes `visibility:hidden`, producing an empty graph canvas. Fixed with a scoped node-visibility rule; no manifest or graph computation changed.
- [P1 judging path] Graph transport sat below the canvas and outside the first viewport. Reordered the standalone Graph shell so timeline, Previous/Next, Reset, Play/Pause, and labelled week slider appear before the canvas.
- [P2 fidelity] Old circular graph nodes and horizontal internal content did not match the straight-edged evidence console. Nodes now use squared surfaces and column layout.
- [P2 system consistency] Loading, error, empty, and 404 states used cream inline styles. Replaced with the shared Forge state panel and explicit recovery actions.

### Final comparison result

- Typography, semantic colors, borders, density, and straight-edged surfaces now match the Judge Mission / Playthrough Inspector visual language.
- Archive exposes filters and report cards in its first viewport. Dossier exposes the gate verdict, navigation, and trace. Graph exposes truth label, transport, and route canvas.
- Archive empty-state recovery and Decision Graph week synchronization passed browser interaction checks.
- Timeline cells are semantic buttons with `aria-current`; transport controls use Phosphor icons and text; slider has a visible label; focus and reduced-motion rules are present.
- A clean Decision Graph tab produced 0 browser warnings and 0 errors.
- `npm run build`: passed. `npm test`: 18/18 passed.
- Offline `judge inspect`, `judge replay`, and Build Week preflight: passed.

### Release data gate

- [P1 content/truth] The tracked `frontend/public-demo` bundle still exposes sanitized aggregate Archive/Dossier data and an illustrative Graph. The UI labels this truthfully, but it does not satisfy the latest decision to show actual competition data on every supporting route.
- Required release action: replace these manifests with committed Build Week campaign/playthrough evidence, retain Replay vs illustrative provenance, then rerun this QA. Do not merely rename the current public labels.

auxiliary visual/interaction result: passed
competition release result: passed with P1 data gate open
