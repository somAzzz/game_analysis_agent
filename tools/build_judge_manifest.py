#!/usr/bin/env python3
"""Generate the hash-pinned, AI-readable Judge Mode table of contents."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ARTIFACTS = {
    "config/build_week_2026_expected_demo_findings.json": ("expected-demo-findings", "build-week-expected-demo-findings-v1"),
    "config/build_week_2026_game_pin.json": ("embedded-demo-pin", "build-week-game-pin-v1"),
    "config/build_week_2026_replay.json": ("replay-smoke-manifest", "persona-replay-manifest-v1"),
    "fixtures/persona_replay/smoke_v1.json": ("replay-smoke-fixture", "persona-replay-fixture-v1"),
    "config/build_week_2026_full_replay.json": ("replay-campaign-manifest", "persona-replay-manifest-v1"),
    "fixtures/persona_replay/build_week_2026_full_v1.json": ("replay-campaign-fixture", "persona-replay-fixture-v1"),
    "examples/build_week_2026/campaign-v1/campaign_manifest.json": ("campaign", "persona-campaign-manifest-v1"),
    "examples/build_week_2026/campaign-v1/campaign_summary.json": ("campaign", "campaign-aggregation-v1"),
    "examples/build_week_2026/campaign-v1/persona_runs.jsonl": ("campaign-rows", None),
    "examples/build_week_2026/campaign-v1/agent_eval.jsonl": ("campaign-evaluation", None),
    "examples/build_week_2026/campaign-v1/llm_calls.jsonl": ("replay-calls", None),
    "examples/build_week_2026/campaign-v1/failure_clusters.json": ("campaign-clusters", "public-failure-clusters-v1"),
    "examples/build_week_2026/campaign-v1/gate_report.json": ("campaign-gate", "campaign-bundle-gate-v1"),
    "examples/build_week_2026/experiment-v1/repair_experiment.json": ("repair-record", "repair-experiment-record-v1"),
    "examples/build_week_2026/experiment-v1/repair_summary.md": ("repair-summary", None),
    "examples/build_week_2026/experiment-v1/comparison.json": ("repair-comparison", None),
    "examples/build_week_2026/experiment-v1/patch.diff": ("candidate-patch", None),
    "examples/build_week_2026/experiment-v1/baseline/fixed.json": ("baseline-fixed", "repair-cohort-evidence-v1"),
    "examples/build_week_2026/experiment-v1/baseline/holdout.json": ("baseline-holdout", "repair-cohort-evidence-v1"),
    "examples/build_week_2026/experiment-v1/patched/fixed.json": ("patched-fixed", "repair-cohort-evidence-v1"),
    "examples/build_week_2026/experiment-v1/patched/holdout.json": ("patched-holdout", "repair-cohort-evidence-v1"),
    "examples/build_week_2026/experiment-v1/gate_report.json": ("repair-gate", "repair-bundle-gate-v1"),
    "docs/reviews/openai_build_week_2026/G2-campaign.review.json": ("independent-campaign-review", "build-week-g2-review-v1"),
    "docs/reviews/openai_build_week_2026/G3-repair.review.json": ("independent-repair-review", "build-week-g3-review-v1"),
    ".agents/skills/playtest-forge/SKILL.md": ("codex-skill", None),
    ".agents/skills/playtest-forge/agents/openai.yaml": ("codex-skill-metadata", None),
    ".agents/skills/playtest-forge/references/automated-testing.md": ("codex-skill-reference", None),
    ".agents/skills/playtest-forge/references/design-contract.md": ("codex-skill-reference", None),
    ".agents/skills/playtest-forge/references/evidence-contract.md": ("codex-skill-reference", None),
    ".agents/skills/playtest-forge/references/evidence-to-parameters.md": ("codex-skill-reference", None),
    ".agents/skills/playtest-forge/references/migration-guide.md": ("codex-skill-reference", None),
    ".agents/skills/playtest-forge/references/repair-protocol.md": ("codex-skill-reference", None),
    ".agents/skills/playtest-forge/references/scenario-balance-economy.md": ("codex-skill-reference", None),
    ".agents/skills/playtest-forge/references/scenario-boundary-robustness.md": ("codex-skill-reference", None),
    ".agents/skills/playtest-forge/references/scenario-content-flow.md": ("codex-skill-reference", None),
    ".agents/skills/playtest-forge/references/session-case-study.md": ("codex-skill-reference", None),
    ".agents/skills/playtest-forge/references/subagent-playthrough.md": ("codex-skill-reference", None),
    ".agents/skills/playtest-forge/references/test-strategy.md": ("codex-skill-reference", None),
    ".agents/skills/playtest-forge/scripts/preflight": ("codex-skill-script", None),
    ".agents/skills/playtest-forge/scripts/run-campaign": ("codex-skill-script", None),
    ".agents/skills/playtest-forge/scripts/verify-repair": ("codex-skill-script", None),
    "tools/verify_expected_demo_findings.py": ("expected-demo-findings-gate", None),
}

for demo_file in sorted((ROOT / "demo/study-in-germany").rglob("*")):
    if demo_file.is_file():
        ARTIFACTS[demo_file.relative_to(ROOT).as_posix()] = ("embedded-demo-source", None)

CLAIMS = [
    {
        "id": "campaign_scale",
        "statement": "The committed Replay campaign contains 18 real-Godot cells and 342 gameplay weeks.",
        "evidence": [
            {
                "path": "examples/build_week_2026/campaign-v1/campaign_summary.json",
                "json_pointer": "/metrics/completed_cells",
                "equals": 18,
            },
            {
                "path": "examples/build_week_2026/campaign-v1/campaign_summary.json",
                "json_pointer": "/metrics/total_weeks",
                "equals": 342,
            },
        ],
    },
    {
        "id": "campaign_provider_health",
        "statement": "Committed deterministic persona-policy Replay decisions are valid with zero fallback and provider errors.",
        "evidence": [
            {
                "path": "examples/build_week_2026/campaign-v1/campaign_summary.json",
                "json_pointer": "/metrics/valid_rate",
                "equals": 1.0,
            },
            {
                "path": "examples/build_week_2026/campaign-v1/campaign_summary.json",
                "json_pointer": "/metrics/fallback_rate",
                "equals": 0.0,
            },
            {
                "path": "examples/build_week_2026/campaign-v1/campaign_summary.json",
                "json_pointer": "/metrics/provider_error_rate",
                "equals": 0.0,
            },
        ],
    },
    {
        "id": "observed_failure_cluster",
        "statement": "All 18 fixed cells enter the selected cashflow/stress failure cluster.",
        "evidence": [
            {
                "path": "examples/build_week_2026/campaign-v1/failure_clusters.json",
                "json_pointer": "/clusters/0/cluster_id",
                "equals": "cashflow-stress-attractor",
            },
            {
                "path": "examples/build_week_2026/campaign-v1/failure_clusters.json",
                "json_pointer": "/clusters/0/member_count",
                "equals": 18,
            },
        ],
    },
    {
        "id": "candidate_rejected",
        "statement": "Codex rejected the candidate because fixed and holdout target membership did not improve.",
        "evidence": [
            {
                "path": "examples/build_week_2026/experiment-v1/repair_experiment.json",
                "json_pointer": "/decision",
                "equals": "rejected",
            },
            {
                "path": "examples/build_week_2026/experiment-v1/comparison.json",
                "json_pointer": "/fixed_relative_reduction",
                "equals": 0.0,
            },
            {
                "path": "examples/build_week_2026/experiment-v1/comparison.json",
                "json_pointer": "/holdout_relative_reduction",
                "equals": 0.0,
            },
        ],
    },
    {
        "id": "codex_centrality",
        "statement": "Codex owned the hypothesis, patch, and accept/reject judgment in the retained core session.",
        "evidence": [
            {
                "path": "examples/build_week_2026/experiment-v1/repair_experiment.json",
                "json_pointer": "/codex/hypothesis_owned_by_codex",
                "equals": True,
            },
            {
                "path": "examples/build_week_2026/experiment-v1/repair_experiment.json",
                "json_pointer": "/codex/patch_owned_by_codex",
                "equals": True,
            },
            {
                "path": "examples/build_week_2026/experiment-v1/repair_experiment.json",
                "json_pointer": "/codex/decision_owned_by_codex",
                "equals": True,
            },
        ],
    },
    {
        "id": "independent_reviews",
        "statement": "The campaign and causal repair experiment pass independent evidence reviews.",
        "evidence": [
            {
                "path": "docs/reviews/openai_build_week_2026/G2-campaign.review.json",
                "json_pointer": "/status",
                "equals": "passed",
            },
            {
                "path": "docs/reviews/openai_build_week_2026/G3-repair.review.json",
                "json_pointer": "/status",
                "equals": "passed",
            },
        ],
    },
]


def build_manifest() -> dict[str, object]:
    artifacts = []
    for relative, (role, schema) in ARTIFACTS.items():
        path = ROOT / relative
        item: dict[str, object] = {
            "path": relative,
            "role": role,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
        if schema is not None:
            item["schema_version"] = schema
        artifacts.append(item)
    return {
        "schema_version": "judge-manifest-v1",
        "project": "Playtest Forge",
        "evidence_revision": "build-week-2026-p3-g3-v1",
        "primary_commands": {
            "inspect": "./judge --mode inspect --offline --json --output-dir -",
            "replay": "./judge --mode replay --offline --json --output-dir -",
        },
        "codex_skill": {
            "name": "playtest-forge",
            "path": ".agents/skills/playtest-forge/SKILL.md",
            "discovery_root": ".agents/skills",
            "explicit_invocation": "$playtest-forge",
            "fallback": "Read .agents/skills/playtest-forge/SKILL.md directly.",
            "review_prompt": (
                "Use $playtest-forge to review the committed automated and "
                "persona-playthrough evidence, explain the rejected candidate, "
                "and propose the next bounded experiment."
            ),
        },
        "artifacts": artifacts,
        "claims": CLAIMS,
        "limitations": [
            "Inspect validates committed evidence; it does not perform a fresh model or Godot run.",
            "The committed persona decisions are deterministic policy-authored Replay fixtures, not recorded or fresh OpenAI responses.",
            "The candidate repair was rejected and is not merged into the game baseline.",
            "Live OpenAI Judge Mode requires a separately supplied server-side API key.",
            "The embedded Study in Germany source is a competition demo, not a complete game.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "judge-manifest.json")
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(build_manifest(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
