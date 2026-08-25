# Product-design materials

This directory retains the frontend design sources, screenshots, prototypes,
concept art, and implementation specifications created for the project. The
competition review and eligibility records that originally surrounded these
materials have been removed; the visual assets themselves remain available.

## Implementation references

- [`CORE_PAGE_IMPLEMENTATION_PLAN.md`](CORE_PAGE_IMPLEMENTATION_PLAN.md) maps
  the two core experiences to the embedded demo and replay data.
- [`PLAYTHROUGH_EVIDENCE_READINESS_PLAN.md`](PLAYTHROUGH_EVIDENCE_READINESS_PLAN.md)
  defines the data needed for truthful playthrough nodes, edges, Persona
  metrics, and route views.
- [`ui-system-v2/PRODUCT_UI_SYSTEM.md`](ui-system-v2/PRODUCT_UI_SYSTEM.md)
  documents the all-route UI system.
- [`persona-runners/README.md`](persona-runners/README.md) documents the
  transparent runner artwork and Persona-to-route mapping.
- [`review-lab/DESIGN_DIRECTION.md`](review-lab/DESIGN_DIRECTION.md) and
  [`review-lab/prototype/`](review-lab/prototype/) retain the editable browser
  prototype and its responsive captures.

The production implementation lives under [`frontend/`](../../../../frontend/),
including the page components, artwork, application tests, and
[`frontend/design-qa.md`](../../../../frontend/design-qa.md).

## Visual assets

- `concepts/` contains the selected replay, Persona, and motion concepts.
- `evidence/` contains seven 1280x720 product screenshots.
- `human-decision-captures/` preserves nine desktop and mobile UI captures
  moved out of the removed competition-review directory.
- `audit-90s-2026-07-17/`, `audit-auxiliary-2026-07-17/`, and `audit-v2/`
  contain historical UI captures without the removed written competition
  audits.
- `review-v3/` contains the editable slide deck, interaction matrix, and native
  image boards.
- `ui-system-v2/audit-before/` and `ui-system-v2/audit-after/` preserve the
  before/after desktop and mobile comparisons.

These files are design references. Runtime behavior and current data contracts
are defined by the application source and tests.
