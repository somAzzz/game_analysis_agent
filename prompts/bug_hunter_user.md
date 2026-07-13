Read the anomaly report bundle below.

The Python detector has already produced:

- `anomalies.jsonl` — one row per anomaly with `kind`, `severity`, `run_id`,
  `week`, `policy`, `evidence`, `message`.
- A distribution of how many runs each anomaly kind touched.

Your job:

1. Group findings into "Confirmed bugs", "Likely bugs", "Worth investigating".
2. For each, produce a row with:
   - `severity` (critical / error / warning / info)
   - `evidence_refs` (run_id / week pairs)
   - `reproduction` (the minimal scenario path that hits the bug)
   - `proposed_fix` (one-line minimum patch in GameState / ActionDef /
     EventResolver / DataRegistry — NOT a full rebalance)
3. Call out any place where the detector's evidence looks weak.
4. Separate observed state from inference. In particular,
   `planned_cost_exceeds_balance` means a selected plan may overcommit the
   starting balance; it does not mean the game executed the charge or allowed
   negative money.

Required output structure:

# Bug Diagnosis

## Top 10 Bugs

For each bug:
- severity
- evidence
- reproduction
- proposed_fix
- confidence (high / medium / low)

## Open Questions

## Recommended Follow-up Tests

Report bundle:

{{REPORT_BUNDLE}}
