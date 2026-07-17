# Local vLLM cohorts A/B — repair and proof closeout

Date: 2026-07-17  
Status: completed; both candidates rejected; neither patch merged  
Scope: A and B only. Cohort C remains campaign-only by owner decision.

## Evidence model

The observation campaigns are real Godot 4.4 playthroughs whose Persona actions were produced by
local vLLM (`qwen3.6-27b-nvfp4`). Repair proof deliberately uses the frozen
`fixture-authoring-policy-v1` decision policy against the same real Godot game. This separates
stochastic hypothesis discovery from deterministic baseline/patched comparison. The Judge UI
shows both labels; local-vLLM campaign evidence is not relabeled as OpenAI evidence.

Each plan was frozen before candidate source inspection, cites exact campaign records, limits the
patch to two allowlisted files and at most 80 changed lines, fixes the visible seeds, and reserves
1042–1044 as unseen holdout seeds. Candidates were committed only in isolated temporary game
worktrees rooted at game commit `348b9fd5501e71ebc7142e10f9068fc1490b5124`.

## Cohort A — crisis stress feedback

- Campaign: `vllm-audit-25seed-cohort-a`; 48/48 cells, 912 weeks, six Personas, 41 campaign target
  members, valid rate 1.0, fallback/provider-error rate 0.0.
- Hypothesis: cashflow crisis weekly drift adds enough stress to make the shared collapse attractor
  difficult to recover from.
- Sensitivity: crisis-only drift caps of 12, 8, and 0 were tried on one fixed seed before formal
  proof. Even the extreme cap produced 6/6 target members and mean maximum stress 100.
- Locked candidate: cap the crisis-only weekly drift increase at 8 and report the actual applied
  delta. Patch: 2 files, +32/−1, hash
  `d4531b3c2655b13f1a64b4017615e78d1cd9ebf595a79e196e3fbc3870dfdb63`.
- Fixed proof: baseline 48/48 → patched 48/48 target members; 0% reduction.
- Unseen holdout: baseline 18/18 → patched 18/18; 0% reduction.
- Decision: **rejected**. `fixed_target` and `holdout_target` failed. All six safety/validity,
  provider-health, persona-preservation, ending, and invariant gates passed.

## Cohort B — survival recovery action

- Campaign: `vllm-audit-25seed-cohort-b`; 48/48 cells, 912 weeks, six Personas, 43 campaign target
  members, valid rate 1.0, fallback/provider-error rate 0.0.
- Hypothesis: `rent_talk_extension` reduces arrears too little and adds stress, so taking the
  intended recovery action cannot escape the shared failure attractor.
- Sensitivity: low, medium, and high recovery effects were tried on one fixed seed. Even the high
  effect produced 6/6 target members and mean maximum stress 100.
- Locked candidate: medium effect (`arrears_amount -360`, `stress -4`) with a focused economy-rule
  validator. Patch: 2 files, +14/−2, hash
  `7818b2e9e8beab8dd6ccc1f2bbb0da300cf77567dd1929bbd04964bb7709cdac`.
- Fixed proof: baseline 48/48 → patched 48/48 target members; 0% reduction.
- Unseen holdout: baseline 18/18 → patched 18/18; 0% reduction.
- Decision: **rejected** with the same two failed causal gates and all six non-causal safety gates
  passing.

## Pressure/burnout cross-check

The earlier game report did detect the owner's observation: 144/150 cells entered sustained
burnout risk, only 9/144 later recovered below stress 80, and mean maximum stress was nearly 100.
Cohort A therefore tests a finding that was present, not a finding the analyzer missed.

The rejected result narrows the causal interpretation. Stress saturation is produced by several
weekly, action, hunger, arrears, and event channels, while the target cells finish in
`cashflow_collapse` with zero mean cash. Removing only the crisis-specific drift increment changes
neither the cash mechanism nor the terminal cluster; maximum stress remains 100 in every formal
cohort. Cohort B independently shows that strengthening one recovery action is also insufficient.
The next experiment must trace the order and cumulative contribution of all pressure channels and
the cashflow ending trigger, rather than increasing either patch magnitude after seeing outcomes.

## Agent and evaluator fixes exposed by this run

The run found one provider-independent toolchain defect: `repair_worktree validate` wrote only a
diff while the proof verifier required a structured `PatchEvidence` JSON file. The CLI now requires
separate `--patch` and `--evidence` outputs and has regression coverage. This defect affected local
and OpenAI workflows equally.

The transport-independent experiment registry now discovers signed Replay, local vLLM, and OpenAI
campaigns from the same verified bundle contracts. A/B are committed as `proof_complete`; C is
truthfully `campaign_complete`. The Judge selector shows source and lifecycle labels, and Human
Review is available only after proof. A/B also retain 96 self-contained Persona/seed views (1,824
nodes and 1,728 actual edges total), each source and derived artifact hash-verified by the existing
playthrough verifier. Static/GitHub Pages fallback now freezes the same three proof-complete
entries, so the selector does not collapse to signed Replay when the Judge API is absent.

The final local image `playtest-forge-judge:ab-final` passed no-network, read-only Inspect
and Replay; Inspect verified 599 signed artifacts. A read-only, dropped-capability
Dashboard/API check returned signed Replay and both A/B experiments with four proof cohorts
and `fixture-authoring-policy-v1`. The first rebuild exposed a missing `frontend/public-demo/`
copy; the Dockerfile now packages those signed fixtures. No registry digest was published.

## Retained paths

- Plans: `config/build_week_2026_repair_plan_vllm_a.json` and
  `config/build_week_2026_repair_plan_vllm_b.json`.
- Campaign targets: `config/build_week_2026_target_vllm_a.json` and
  `config/build_week_2026_target_vllm_b.json`.
- Public experiment bundles: `examples/build_week_2026/experiments/`.
- Frontend full paths: `frontend/public-demo/experiments/`.
- Runtime private/public records: `reports/repair-experiments/` (ignored; reproducible working
  evidence, not the committed evaluator source).
