# Option 1 offline review boards

Status: `rendered · visually-verified · no-overflow`

These 1536×1024 boards provide the complete v3 design review without requiring
Figma. They can also be uploaded later as a locked visual reference. They are
review artifacts, not production frontend screenshots.

| File | Review purpose | SHA-256 |
| --- | --- | --- |
| `01-evidence-overview.png` | Judge Mission thesis, actual campaign counts, truth boundary, and frontend approval gate | `c6ef57bb440f5b9b441de542c81204ee419af90e89d130719dcbc25c0154f96f` |
| `02-interaction-states.png` | S1–S6 matrix with actual Money W1/W3/W19 facts and graph semantics | `0059369c18350e402c0ed4e1a76a3759951eda4c812615ad57569c80de0790e9` |
| `03-persona-motion.png` | Six human strategy Personas, five motion states, and evidence/motion boundaries | `51d9821872791e13fef4f02526b20d9ec241885921ce0a442f2e4548cdb6091f` |

The editable three-slide source is
[`../option-1-figma-import-review-v3.pptx`](../option-1-figma-import-review-v3.pptx),
SHA-256
`73a9c6454915e123f599976ebe8c11f597fb1143c5e401b38d331abc310386df`.

## Evidence boundary

- Actual campaign summary: 18/18 cells, 342 observed week nodes, 324 actual
  transitions, 1.0 valid rate, zero fallback, and 18 target members.
- Actual selected cell: `money · seed 42`.
- Actual highlighted states: W1 arrival, W3 first cashflow-stress attractor, and
  W19 `cashflow_collapse` ending.
- Truth label: `prerecorded-real-godot-replay`.
- Replay proves reproducibility. It does not prove a fresh OpenAI call.
- The routes in the Persona motion storyboard are decorative motion references.
  They are never evidence and must not be used as Inspector graph data.

## Visual QA

1. Each source slide was exported directly at 1536×1024.
2. Each exported PowerPoint slide was rendered independently and inspected.
3. A clipped header and an overlapping risk label found in the first pass were
   corrected and rerendered.
4. The final PowerPoint passed `slides_test.py` with no overflow detected.
5. The production frontend approval gate remains visible on the overview and
   Persona boards.
