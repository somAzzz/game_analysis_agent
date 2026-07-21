# PLAYTEST FORGE

> From diverse AI playtests to evidence-backed, Codex-verified game repairs.

Category: Developer Tools

## Inspiration

AI playtesting produces diverse feedback, but game teams still struggle to turn
that feedback into reproducible fixes. Scripted tests verify rules, while LLM
agents explore different goals—but neither alone proves that a repair works.

I built PLAYTEST FORGE while testing my own Godot game demo. The goal was to
create one auditable loop: **Campaign → Diagnose → Repair → Prove**.

## What it does

GPT-5.6 Luna plays the game through bounded personas. Godot remains the source
of truth, and Python records actions, state changes, and evidence references.

Codex is the main agent. It reviews the evidence and source code, selects one
causal hypothesis, applies a constrained candidate repair, and verifies it with
fixed and unseen holdout seeds. Developers retain the final decision.

## How we built it

- Godot 4.4 executes the real game demo.
- Python and Pydantic provide typed gameplay and evidence contracts.
- The OpenAI Responses API supplies GPT-5.6 Luna persona decisions.
- A Codex Skill directs testing, diagnosis, repair, and verification.
- React presents the evidence, while hash-pinned Replay works offline.

Live OpenAI campaigns and deterministic Replay are labeled separately. Replay
proves reproducibility; it is never presented as a fresh model call.

## Challenges we ran into

The hardest problem was separating a better metric from a proven repair. One
candidate passed its focused validator and improved mean cash, but the target
failure did not improve on fixed or holdout seeds. PLAYTEST FORGE rejected it.

We also made the committed evidence reviewable without exporting game data or
rerunning an expensive persona campaign.

## Accomplishments that we're proud of

Codex found an unexpected bilingual choice-identity bug in the unfinished demo.
It traced the issue, made a bounded fix, and accepted it only after fixed and
unseen-holdout checks passed.

The project demonstrates both outcomes: one correctness fix was accepted with
evidence; one ineffective balance candidate was rejected and never merged.

## How to judge it

```bash
./judge --mode inspect --offline --json --output-dir -
./judge --mode replay --offline --json --output-dir -
```

Inspect needs only Python 3.9+. Replay uses the locked `uv` environment. Neither
requires a GPU, API key, Docker, Godot, network access, game rebuild, or fresh
model/agent rerun. Both return machine-readable pass/fail JSON.

## What we learned

Agents are useful for exploration, but confidence is not proof. Reliable repair
requires exact evidence, bounded edits, protected tests, and unseen holdouts.

## What's next for PLAYTEST FORGE

Next, I will expose the existing typed services through MCP and add more game
adapters without weakening the evidence gates.
