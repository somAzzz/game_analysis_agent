# Attribution and asset provenance

Playtest Forge is released under the [MIT License](LICENSE). Third-party
packages keep their own licenses; their package metadata and lockfiles are the
authoritative version record.

## Major third-party components

- React, React DOM, React Router, Vite, Vitest, Phosphor Icons, React Flow
  (`@xyflow/react`), Dagre, and the OpenAI Python SDK are used under their
  respective upstream licenses.
- Godot Engine is MIT-licensed. The engine itself is not vendored here.
- The embedded `demo/study-in-germany` snapshot and competition distribution
  are covered by the maintainer ownership attestation recorded in
  `config/build_week_2026_scope.json`; its exact source identity and hashes are
  recorded in `config/build_week_2026_game_pin.json` and
  `demo/study-in-germany/.playtest-forge-source.json`.

## Competition artwork

The strategy-persona characters, mission map, review compositions, and their
two-frame motion variants were generated specifically for this project and
then edited and integrated by the project team. They depict original fictional
personas and are distributed with this repository under its MIT license. They
do not use the OpenAI, Codex, Godot, or third-party game logos as characters.

The interface uses system font fallbacks and may request Fraunces, Newsreader,
and IBM Plex Mono from Google Fonts when network access is available. Those
font families are published under the SIL Open Font License; no font binaries
are committed in this repository.

Names and marks belonging to OpenAI, Godot, GitHub, and other projects remain
the property of their respective owners. Their mention describes integration
or compatibility and does not imply endorsement.
