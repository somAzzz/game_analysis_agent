# Gameplay Agent Guide

`game_analysis_agent` ships **seven** agents. Three of them (`balance`,
`content_qa`, `event_graph`) existed in the v0.1 skeleton; the rest
(`bug_hunter`, `boundary_prober`, `value_reviewer`, `interactive_player`)
are added in v0.2 along with the anomaly / value detectors that feed
them.

| Slug | Inputs | Outputs | Temperature | Role |
|---|---|---|---|---|
| `balance` | `summary.json` + CSVs | `agent_diagnosis.md`, `tuning_proposal.md` | 0.2 | Diagnose ending distribution, attribute curves, action dominance. |
| `content_qa` | Event/choice/ending text + CSVs | `content_issues.md` | 0.15 | Review wording, choice trade-offs, German/Chinese/English consistency. |
| `event_graph` | `event_graph.json` + CSVs | `event_graph_report.md` | 0.1 | Audit trigger graph (broken links, cycles, contradictory flags). |
| `bug_hunter` | `anomalies.jsonl` + `summary.json` + raw runs | `bug_diagnosis.md` | 0.2 | Convert anomaly clusters into ranked bug hypotheses with reproduction steps. |
| `boundary_prober` | `boundary_runs.jsonl` + balance CSVs | `boundary_report.md` | 0.2 | Review extreme-scenario outcomes, flag dead-ends and numeric drift. |
| `value_reviewer` | `value_report.json` + balance CSVs | `value_review.md` | 0.15 | Turn pick-rate / choice-bias / ending-dominance findings into tuning proposals. |
| `interactive_player` | (no inputs) drives tools | `playthrough.jsonl`, `playthrough_summary.md` | 0.3 | Play the game end-to-end via tool calling. |

## Pipeline overview

```text
              ┌─────────────────────────────────────────────────────┐
              │                  Godot (study-in-germany)          │
              │  RunSimulation.gd ── raw_runs.jsonl                │
              │  RunBoundaryProbe.gd ── boundary_runs.jsonl         │
              │  ExportEventGraph.gd ── event_graph.json            │
              │  RunInteractiveProbe.gd ── tool-loop wrapper        │
              └─────────────────────────────────────────────────────┘
                                  │
                                  ▼
              ┌─────────────────────────────────────────────────────┐
              │                  Deterministic Python              │
              │  analytics.py            (ending / pick / weekly)  │
              │  anomaly_detector.py     (invariants, spikes)      │
              │  value_analyzer.py       (dominant / dead actions) │
              │  bug_summarizer.py       (anomalies → markdown)    │
              └─────────────────────────────────────────────────────┘
                                  │
                                  ▼
              ┌─────────────────────────────────────────────────────┐
              │                LLM agents (vllm / sglang / deepseek) │
              │  bug_hunter / boundary_prober / value_reviewer       │
              │  balance / content_qa / event_graph                  │
              │  interactive_player (tool calling)                   │
              └─────────────────────────────────────────────────────┘
```

## When to use which

* **balance** — your first stop after every simulation batch. Produces
  the canonical "diagnosis + tuning proposal" pair.
* **bug_hunter** — when `anomalies.jsonl` has any rows whose severity is
  `error` or `critical`. The agent reads the structured anomalies + raw
  runs and proposes concrete fixes.
* **boundary_prober** — when you change a flag, an action's
  `cost_money`, or the `DifficultyConfig` and want to know whether the
  extremes still produce reasonable outcomes.
* **value_reviewer** — every time the balance agent proposes a tuning
  change, run `value_reviewer` to cross-check the data behind the claim.
  It also flags cases where the policy never visited the relevant
  state-space regime (a "must-pick" action can look like an underused
  action if the simulator always avoids its trigger condition).
* **interactive_player** — for design review. It plays one playthrough
  with the LLM in the driver's seat and writes a postmortem. Useful when
  you want to see how a "natural" sequence of decisions interacts with
  the simulator, especially the schedule / visa / mental-health /
  romance graphs.

## Determinism guarantees

* **Statistics are deterministic.** Given the same `raw_runs.jsonl`,
  `analytics.py` always emits the same CSVs. The CSV order is sorted by
  policy → metric → identifier to keep diffs stable.
* **Anomaly detection is deterministic.** The detector is a pure
  function over `(run, week)`; no random seeds are needed.
* **Value findings are deterministic.** The `analyze_values` function
  groups by `(policy, action_id)` / `(policy, event_id)` /
  `(policy, ending_id)` and applies the same thresholds each time.
* **LLM outputs are NOT deterministic.** All LLM-backed agents are
  documented to be "stochastic narrative"; do not put them in CI gating
  unless you mock the LLM client.

## Audit trail

Every chat call produces a
:class:`game_analysis_agent.schemas.LLMCall` row (Pydantic model with
prompt / response text, token usage, latency, error). Every tool call
produces a :class:`ToolExecutionEvent` row.

`InteractivePlayerAgent.run` aggregates both into an
:class:`AgentRunReport` and returns the list alongside the persisted
artifacts. Future UI work can render these directly.