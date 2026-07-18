# Playtest Forge

> A Codex-led causal QA loop for simulation games: observe with persona
> playthroughs, propose one bounded repair, and require fixed plus unseen
> holdout evidence before accepting it.

Category: Developer Tools

Status: pre-release draft with the OpenAI evidence row complete; remaining
blockers are the video, non-builder review records, final URLs/team checks, and
current-revision delivery closeout. Do not publish this text until
`RELEASE_CHECKLIST.md` is complete.

## The problem

Game simulations can pass unit and content validators while still funneling
very different players into the same systemic failure. A plausible local fix
can improve one visible metric and still leave the player-level failure intact.
Teams need more than an agent that writes a patch: they need an auditable loop
that can reject its own work.

## What Playtest Forge does

Codex is the main agent. It plans a focused persona campaign, cites exact
gameplay facts, freezes one causal hypothesis and change budget, edits an
isolated Godot worktree, runs fixed-seed and unseen-holdout cohorts, and makes
the final accept/reject judgment. The action-provider boundary supports
deterministic Replay evidence and a bounded OpenAI Responses API persona mode;
the browser never receives the server key.

The signed repair demonstration is deliberately labeled a deterministically
authored persona-policy Replay fixture, not a recorded LLM run or live call.
18 persona/seed cells produced 342 real-Godot gameplay weeks. All 18 campaign
cells entered the selected cashflow/stress failure cluster. The committed
campaign recorded 100% valid decisions, 0% fallback, and 0% provider errors.

A retained live OpenAI gpt-5.6-luna campaign completed all six personas at seed
42 with 114 gameplay records, 0% fallback, and 0% provider errors. The static
Judge labels it CAMPAIGN ONLY and provides exact persona/seed replay; it is not
presented as fixed/holdout repair proof.

## The repair that did not earn a merge

In the retained core task, Codex owned the hypothesis, bounded patch, and
accept/reject judgment. Codex proposed one bounded candidate: 2 allowlisted
files, 35 additions, and 5 deletions. Its focused Godot validator passed and
mean cash improved—but that was not the acceptance criterion. Fixed and unseen
holdout cohorts both reduced target-cluster membership by 0%, so Codex rejected
the candidate and it was not merged.

That rejection is the product outcome: Playtest Forge stopped a reasonable,
locally passing patch from being promoted without causal evidence.

## How to judge it

```bash
./judge --mode inspect --offline --json --output-dir -
./judge --mode replay --offline --json --output-dir -
```

Inspect needs only Python 3.9+. Replay uses the locked Python environment. Both
are repository-only, offline, non-interactive, and return machine-readable
pass/fail results. The public UI tells the same Campaign → Repair → Proof story
and labels its static evidence. Optional live OpenAI mode is fail-closed when a
server key or real game runtime is absent.

## OpenAI and Codex roles

- Codex: main planner and implementation agent; evidence citation, hypothesis,
  constrained source edit, verification plan, and final rejection.
- OpenAI Responses API persona provider: live `gpt-5.6-luna` action subagent
  behind the same bounded decision contract. Its retained six-persona campaign
  passed public evidence gates; no repair decision is inferred from that run.
- Replay provider: deterministic persona-policy fixture for unknown/restricted
  judges; never relabeled as a recorded or fresh model call.

Core Codex task: 019f6816-fe0d-78a2-9001-1890b32ef820.

## Links (release blockers)

- Repository: [github.com/somAzzz/game_analysis_agent](https://github.com/somAzzz/game_analysis_agent)
- Public Judge UI: [somazzz.github.io/game_analysis_agent](https://somazzz.github.io/game_analysis_agent/)
- YouTube demo under 3:00: `{{YOUTUBE_URL}}`
- Docker evaluator: build the current submission branch with
  `docker build -f Dockerfile.judge .`; no old digest is claimed for this
  revision.

## Current limitations

The recorded candidate did not repair the target failure. The live OpenAI
campaign is complete but has not been used for fixed/holdout repair proof.
Manual timing comparison, independent clean-room review, current-revision
delivery closeout, and the final video must still be completed before release
claims advance. Local-model vLLM remains optional and is not required to judge
the project.
