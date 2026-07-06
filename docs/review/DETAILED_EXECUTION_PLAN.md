# Detailed Execution Plan

This plan covers the gaps found in `ALIGNMENT_AUDIT.md`. It has been executed
in the current remediation pass.

## P1-A: Event Graph Untriggered Reasons

Files:

- `src/game_analysis_agent/agents/event_graph.py`
- `prompts/event_graph_agent_user.md`
- `tests/test_agents_registry.py`

Implementation:

1. Load `raw_runs.jsonl` and `event_graph.json` from `report_dir` when present.
2. Count event triggers from `weekly_log[].triggered_event_id` and legacy `event_id`.
3. For events with zero or very low trigger count, render a deterministic markdown block:
   event id, trigger count, trigger expression/conditions, and a coarse missing-reason hint.
4. Inject the block through `{{UNTRIGGERED_EVENTS}}` before `{{REPORT_BUNDLE}}`.

Validation:

- Unit test prompt rendering with a tiny `event_graph.json` and `raw_runs.jsonl`.
- Assert the rendered prompt contains `## Untriggered Events` and the missing event id.
- Done in `tests/test_agents_registry.py`.

## P1-B: Content QA Choice-Structure Findings

Files:

- `src/game_analysis_agent/agents/content_qa.py`
- `prompts/content_qa_agent_user.md`
- `tests/test_agents_registry.py`

Implementation:

1. Load `event_graph.json`.
2. For each event choice, inspect text plus common effect fields:
   `effects`, `success_effects`, `failure_effects`, `stat_effects`, and `costs`.
3. Emit deterministic findings for:
   - `all_choices_positive`
   - `missing_failure_cost`
   - `choice_effects_too_similar`
   - `duplicate_choice_text`
4. Inject the markdown table through `{{CHOICE_STRUCTURE_FINDINGS}}`.

Validation:

- Unit test prompt rendering with a tiny event graph fixture.
- Assert the rendered prompt contains `## Choice Structure Findings` and at least one issue id.
- Done in `tests/test_agents_registry.py`.

## P0-Fix: Hunger Threshold Drift

Files:

- `src/game_analysis_agent/anomaly_semantics.py`
- `tests/test_anomaly_semantics.py`

Implementation:

1. Replace the hard-coded `hunger >= 90` with `hunger >= survival_hunger`.
2. Include the actual threshold in evidence and message.
3. Add a test case where six weeks of `hunger = 86` triggers `hunger_ignored_too_long`.

Validation:

- `pytest tests/test_anomaly_semantics.py tests/test_agents_registry.py -q`
- If time allows, run the full suite or the existing documented partial suite.
- Done with `uv run pytest tests/ -q` -> 106 passed.
