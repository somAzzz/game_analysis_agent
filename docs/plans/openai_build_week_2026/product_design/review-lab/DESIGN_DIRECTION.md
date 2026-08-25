# Review Lab design direction

Status: `approved-and-migrated`

Approval record: the option-1 Review Lab direction was approved on 2026-07-17
and migrated to the formal Judge Mission and Playthrough Inspector frontend.
This document and the prototype remain the visual/interaction reference; the
implementation and QA record live in `frontend/src/components/competition/`,
`frontend/src/pages/PlaythroughInspectorPage.tsx`, and `frontend/design-qa.md`.

## Subject, audience, and single job

- Subject: a forensic mission console for game-agent playtesting.
- Audience: game developers and competition judges.
- Single job: make the 90-second story “the patch passed a focused test, but
  the actual playthrough evidence still rejected it” understandable and
  inspectable.

## Selected visual targets

- `../concepts/option-1-actual-replay-review-v2.png` — layout, hierarchy, graph
  grammar, evidence density, and color balance.
- `../concepts/persona-motion-storyboard-v1.png` — character identity and motion
  states only; its decorative paths are not evidence.
- `assets/persona-roster-v2.png` — production roster image for six aligned
  Persona interaction targets. The Visa character has exactly two arms: one
  holds a checklist and one adjusts the glasses.

## Compact token system

| Role | Value | Meaning |
| --- | --- | --- |
| Night map | `#071318` | primary game-world canvas |
| Evidence panel | `#0c1d23` | logs, drawers, and state records |
| Chalk | `#edf7f3` | primary readable copy |
| Fog | `#9bb0af` | secondary metadata |
| Recorded cyan | `#77ddd4` | observed state and selected Persona |
| Legal amber | `#f2c66d` | legal but unexecuted option / hover |
| Terminal coral | `#ff665f` | failure and rejected verdict only |

Typography reuses the product's existing Judge Mode stack: restrained
`Fraunces` for the mission thesis, `Newsreader` for explanatory copy, and
`IBM Plex Mono` for controls, hashes, logs, and evidence labels.

## Layout concept

```text
┌ mission header ───────────── verdict / truth label ┐
│ six-strategy roster + aligned hover hit areas      │
├ campaign facts ───────────── selected detail drawer┤
│ actual route ribbon + moving Money Persona         │
├ node inspector ───────────── signed evidence log ──┤
│ previous / play / next / W1 W3 W19 / review states │
└ production approval gate                           ┘
```

Desktop is a dense 16:10 judge-room composition. Tablet stacks the drawer
below the route. Mobile becomes a review reader: the roster scrolls
horizontally, the route remains complete, and primary playback controls stay
visible.

## Signature element

The memorable interaction is the same selected strategy person appearing in
two roles: first as a squad member whose contract can be inspected, then as the
runner who advances across the signed route. One synchronized step updates the
person, node, event, state delta, and evidence log together.

## Uniqueness critique and revision

An initial dashboard-grid approach would have looked like generic analytics.
It was rejected. The prototype instead uses one continuous mission surface:
topographic texture, roster, route ribbon, evidence console, and ledger rules
all describe a game run. Cards are reserved for actual contracts or evidence
records rather than used as decorative containers.

The one deliberate aesthetic risk is placing painterly chibi characters inside
a rigorous forensic evidence console. The contrast works because character
motion communicates strategy identity while the surrounding typography and
hashes keep every claim auditable.

## Evidence boundary

- Truth label: `prerecorded-real-godot-replay`.
- Replay proves reproducibility, not a fresh OpenAI call.
- Solid cyan edges are recorded transitions.
- Amber stubs are legal options at an observed state, not alternate futures.
- No projected counterfactual node or ending may be drawn.
