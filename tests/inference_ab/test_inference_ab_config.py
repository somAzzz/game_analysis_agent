from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "inference_ab"


def _dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def test_inference_profiles_change_only_the_intended_optimization() -> None:
    apc = _dotenv(CONFIG / "apc_only.env")
    mtp = _dotenv(CONFIG / "mtp3_only.env")

    common = {
        "LLM_MODEL",
        "LLM_SERVED_MODEL_NAME",
        "LLM_MAX_MODEL_LEN",
        "LLM_MAX_NUM_SEQS",
        "LLM_MAX_NUM_BATCHED_TOKENS",
        "LLM_GPU_MEMORY_UTILIZATION",
        "VLLM_BIND_PORT",
        "CUDA_VISIBLE_DEVICES",
        "HF_HUB_ENABLE_HF_TRANSFER",
    }
    assert {key: apc[key] for key in common} == {key: mtp[key] for key in common}
    assert apc["LLM_ENABLE_PREFIX_CACHING"] == "1"
    assert apc["LLM_ENABLE_MTP"] == "0"
    assert mtp["LLM_ENABLE_PREFIX_CACHING"] == "0"
    assert mtp["LLM_MAMBA_CACHE_MODE"] == "none"
    assert mtp["LLM_ENABLE_MTP"] == "1"
    assert mtp["LLM_MTP_NUM_SPECULATIVE_TOKENS"] == "3"


def test_inference_ab_plan_binds_profiles_workloads_metrics_and_artifacts() -> None:
    plan = yaml.safe_load((CONFIG / "plan.yaml").read_text(encoding="utf-8"))

    assert plan["schema_version"] == "inference-ab-v1"
    assert set(plan["variants"]) == {"apc_only", "mtp3_only"}
    assert plan["variants"]["apc_only"]["env_file"].endswith("apc_only.env")
    assert plan["variants"]["mtp3_only"]["num_speculative_tokens"] == 3
    assert plan["execution"]["repetitions_per_scenario_arm"] == 3
    assert (
        plan["execution"]["restart_server_before_every_scenario_arm"]
        is True
    )
    long_horizon = plan["workloads"]["long_horizon_campaigns"]
    assert long_horizon["semester"]["max_weeks"] == 20
    assert long_horizon["semester"]["minimum_completed_weeks"] == 18
    same = long_horizon["scenarios"]["same_persona_multi_seed"]
    assert same["personas"] == ["newbie"]
    assert same["seeds"] == [42, 43, 44, 45]
    different = long_horizon["scenarios"]["different_personas_single_seed"]
    assert different["personas"] == ["newbie", "study", "money", "social"]
    assert different["seeds"] == [42]
    assert long_horizon["physical_cells_per_arm"] == 8
    assert long_horizon["worst_case_model_calls_full_experiment"] == 1920
    assert (
        long_horizon["rerun_overlapping_newbie_seed_42_per_scenario"]
        is True
    )
    assert plan["workloads"]["frozen_trace_replay"]["passes"] == [
        {"id": "cold", "ordinal": 1},
        {"id": "warm", "ordinal": 2},
    ]
    assert plan["workloads"]["diagnostic_sweep"]["concurrency"] == [1, 4]
    expansions = plan["workloads"]["optional_expansions"]
    assert (
        expansions["full_factorial_confirmation"]["worst_case_model_calls"]
        == 1280
    )
    assert expansions["edge_persona_holdout"]["personas"] == ["visa", "slacker"]
    assert (
        plan["primary_decision"]["confidence_method"]
        == "hierarchical_paired_bootstrap"
    )
    assert "vllm:prefix_cache_hits_total" in plan["server_metrics"]
    assert "vllm:spec_decode_num_accepted_tokens_total" in plan["server_metrics"]
    assert "comparison.html" in plan["artifacts"]["required"]
