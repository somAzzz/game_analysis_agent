# Portfolio Notes

This project is intended to demonstrate AI-native product engineering around a
real game QA workflow, not just a prompt wrapper.

## What It Demonstrates

- Agent orchestration: multiple specialized agents review balance, content,
  value alignment, event graph structure, bug signals, boundary states, and
  interactive playthroughs.
- Context engineering: raw simulation traces are converted into compact,
  typed report bundles before an LLM sees them.
- Game QA automation: headless Godot runners produce Monte Carlo, boundary,
  event graph, and interactive playtest artifacts.
- Structured reports: JSON, JSONL, CSV, Markdown, manifests, and dashboards are
  emitted as traceable build products.
- Quality gates: configurable thresholds turn analyzer output into reviewable
  pass/warn/fail signals.
- Local LLM deployment: the default path supports an OpenAI-compatible local
  vLLM endpoint for private development runs.
- Dashboard productization: static HTML and React dashboards make the analysis
  browsable for non-engineering reviewers.

## Why It Matters

Most game QA automation stops at scripts and logs. This project treats the QA
pipeline as a product surface: repeatable runs, explicit data contracts,
audit-friendly manifests, role-specific agents, and a dashboard that lets a
designer or hiring reviewer understand the result without reproducing the full
game environment.

## Current Boundary

Interactive LLM playtesting is implemented as an orchestration target. Full
real-time Godot stepping depends on the target game exposing the required probe
script and data contracts.
