#!/usr/bin/env python3
"""Generate the auditable APC versus MTP report from completed long campaigns."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import random
import re
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

APC = "apc-only"
MTP = "mtp3-only"
COLORS = {
    APC: "#2563eb",
    MTP: "#e11d48",
    "Input kTok/request": "#0f766e",
    "Output kTok/request": "#7c3aed",
}
SCENARIO_LABELS = {
    "same-persona": "Same persona / 4 seeds",
    "different-personas": "4 personas / same seed",
}


def json_stream(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    offset = 0
    values = []
    while offset < len(text):
        while offset < len(text) and text[offset].isspace():
            offset += 1
        if offset >= len(text):
            break
        value, offset = decoder.raw_decode(text, offset)
        if isinstance(value, dict):
            values.append(value)
    return values


def campaign_result(path: Path) -> dict[str, Any]:
    values = json_stream(path)
    matches = [
        value
        for value in values
        if value.get("schema_version") == "persona-campaign-service-result-v1"
    ]
    if not matches:
        raise ValueError(f"campaign result missing from {path}")
    return matches[-1]


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def bootstrap_ci(values: list[float], *, samples: int = 20_000) -> tuple[float, float]:
    rng = random.Random(42)
    means = [
        statistics.mean(rng.choice(values) for _ in range(len(values)))
        for _ in range(samples)
    ]
    return percentile(means, 0.025), percentile(means, 0.975)


def parse_prom(path: Path) -> dict[tuple[str, str], float]:
    values: dict[tuple[str, str], float] = {}
    pattern = re.compile(r"^([^\s{]+)(?:\{([^}]*)\})?\s+([^\s]+)$")
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"):
            continue
        match = pattern.match(raw)
        if not match:
            continue
        name, labels, number = match.groups()
        try:
            value = float(number)
        except ValueError:
            continue
        values[(name, labels or "")] = value
    return values


def prom_delta(before: dict, after: dict, metric: str, label: str | None = None) -> float:
    total = 0.0
    for (name, labels), value in after.items():
        if name != metric or (label is not None and label not in labels):
            continue
        total += value - before.get((name, labels), 0.0)
    return total


def gpu_summary(path: Path) -> dict[str, float]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for row in csv.reader(handle):
            if len(row) < 6 or row[1].strip() != "0":
                continue
            try:
                rows.append(
                    {
                        "util": float(row[2]),
                        "memory": float(row[3]),
                        "power": float(row[4]),
                        "clock": float(row[5]),
                    }
                )
            except ValueError:
                continue
    if not rows:
        return {"samples": 0, "mean_util": 0, "mean_power": 0, "energy_wh": 0}
    return {
        "samples": len(rows),
        "mean_util": statistics.mean(row["util"] for row in rows),
        "mean_power": statistics.mean(row["power"] for row in rows),
        "mean_memory_mib": statistics.mean(row["memory"] for row in rows),
        "mean_clock_mhz": statistics.mean(row["clock"] for row in rows),
        "energy_wh": sum(row["power"] for row in rows) / 3600,
    }


def discover(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    attempts = []
    for timing_path in sorted(root.glob("r*/**/timing.json")):
        relative = timing_path.relative_to(root)
        if len(relative.parts) != 4:
            continue
        repetition_name, scenario, arm_name, _ = relative.parts
        if scenario not in SCENARIO_LABELS:
            continue
        variant = MTP if arm_name.startswith("mtp3-only") else APC
        directory = timing_path.parent
        output = directory / "campaign-output.json"
        if not output.exists():
            continue
        try:
            result = campaign_result(output)
        except ValueError:
            result = {
                "status": "failed_without_service_result",
                "cells": {},
            }
        timing_text = timing_path.read_text(encoding="utf-8")
        timing = json.loads(timing_text[timing_text.index("{") :])
        attempts.append(
            {
                "repetition": int(repetition_name[1:]),
                "scenario": scenario,
                "variant": variant,
                "arm_name": arm_name,
                "directory": directory,
                "result": result,
                "timing": timing,
                "valid": (
                    result.get("status") == "passed"
                    and result.get("cells", {}).get("completed") == 4
                    and result.get("cells", {}).get("failed") == 0
                    and result.get("cells", {}).get("partial") == 0
                    and int(timing.get("exit_status", 1)) == 0
                ),
            }
        )
    selected = {}
    for attempt in attempts:
        key = (attempt["repetition"], attempt["scenario"], attempt["variant"])
        if key not in selected or (attempt["valid"] and not selected[key]["valid"]):
            selected[key] = attempt
    arms = sorted(selected.values(), key=lambda row: (
        row["repetition"], row["scenario"], row["variant"]
    ))
    if len(arms) != 12 or not all(arm["valid"] for arm in arms):
        raise ValueError("expected exactly 12 valid selected long-horizon arms")
    return arms, attempts


def enrich_arms(project: Path, arms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for arm in arms:
        result = arm["result"]
        bundle = project / result["bundle"]
        calls = [
            json.loads(line)
            for line in (bundle / "llm_calls.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        runs = [
            json.loads(line)
            for line in (bundle / "persona_runs.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        before = parse_prom(arm["directory"] / "server-metrics-before.prom")
        after = parse_prom(arm["directory"] / "server-metrics-after.prom")
        queries = prom_delta(before, after, "vllm:prefix_cache_queries_total")
        hits = prom_delta(before, after, "vllm:prefix_cache_hits_total")
        drafts = prom_delta(before, after, "vllm:spec_decode_num_draft_tokens_total")
        accepted = prom_delta(before, after, "vllm:spec_decode_num_accepted_tokens_total")
        stopped = prom_delta(
            before, after, "vllm:request_success_total", 'finished_reason="stop"'
        )
        length = prom_delta(
            before, after, "vllm:request_success_total", 'finished_reason="length"'
        )
        arm.update(
            {
                "calls": calls,
                "runs": runs,
                "wall_seconds": float(arm["timing"]["wall_time_seconds"]),
                "weeks": int(result["weeks"]),
                "throughput": int(result["weeks"])
                / float(arm["timing"]["wall_time_seconds"])
                * 3600,
                "input_tokens": sum(
                    int(call["metadata"]["usage"].get("input_tokens") or 0) for call in calls
                ),
                "output_tokens": sum(
                    int(call["metadata"]["usage"].get("output_tokens") or 0) for call in calls
                ),
                "physical_requests": sum(
                    int(call["metadata"].get("attempt_count") or 1) for call in calls
                ),
                "repair_rate": sum(
                    call["metadata"].get("parse_status") == "repaired" for call in calls
                )
                / len(calls),
                "fallback_rate": sum(bool(run["fallback_used"]) for run in runs) / len(runs),
                "provider_error_rate": sum(bool(run["provider_error"]) for run in runs)
                / len(runs),
                "cache_hit_rate": hits / queries if queries else 0.0,
                "mtp_acceptance_rate": accepted / drafts if drafts else 0.0,
                "length_finish_rate": length / (length + stopped) if length + stopped else 0.0,
                "prom": {
                    "prefix_queries": queries,
                    "prefix_hits": hits,
                    "draft_tokens": drafts,
                    "accepted_tokens": accepted,
                    "stop_requests": stopped,
                    "length_requests": length,
                },
                "gpu": gpu_summary(arm["directory"] / "gpu-metrics.csv"),
            }
        )
    return arms


def aggregate_weekly(arms: list[dict[str, Any]]) -> dict:
    cell_weeks = defaultdict(lambda: {"latency_ms": 0.0, "input_tokens": 0, "output_tokens": 0, "requests": 0})
    for arm in arms:
        for call in arm["calls"]:
            key = (
                arm["scenario"],
                arm["variant"],
                arm["repetition"],
                call["persona"],
                int(call["seed"]),
                int(call["week"]),
            )
            value = cell_weeks[key]
            value["latency_ms"] += float(call["metadata"].get("latency_ms") or 0)
            value["input_tokens"] += int(call["metadata"]["usage"].get("input_tokens") or 0)
            value["output_tokens"] += int(call["metadata"]["usage"].get("output_tokens") or 0)
            value["requests"] += int(call["metadata"].get("attempt_count") or 1)
    weekly = {}
    for scenario in SCENARIO_LABELS:
        for variant in (APC, MTP):
            for week in range(1, 20):
                rows = [
                    value
                    for key, value in cell_weeks.items()
                    if key[0] == scenario and key[1] == variant and key[-1] == week
                ]
                weekly[(scenario, variant, week)] = {
                    metric: statistics.median(float(row[metric]) for row in rows)
                    for metric in ("latency_ms", "input_tokens", "output_tokens", "requests")
                }
    return {"cell_weeks": cell_weeks, "weekly": weekly}


def svg_start(title: str, subtitle: str, *, height: int = 520) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {height}">',
        "<style>text{font-family:Inter,Arial,sans-serif;fill:#172033}.title{font-size:24px;font-weight:700}.sub{font-size:13px;fill:#64748b}.axis{stroke:#94a3b8;stroke-width:1}.grid{stroke:#e2e8f0;stroke-width:1}.label{font-size:12px}.small{font-size:10px;fill:#64748b}</style>",
        '<rect width="1000" height="100%" fill="#ffffff"/>',
        f'<text x="52" y="38" class="title">{html.escape(title)}</text>',
        f'<text x="52" y="60" class="sub">{html.escape(subtitle)}</text>',
    ]


def finish_svg(parts: list[str], path: Path) -> None:
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def bar_chart(path: Path, title: str, subtitle: str, labels: list[str], series: dict[str, list[float]], *, suffix: str = "") -> None:
    parts = svg_start(title, subtitle)
    left, top, width, height = 80, 100, 860, 330
    maximum = max(max(values) for values in series.values()) * 1.15 or 1
    for tick in range(6):
        value = maximum * tick / 5
        y = top + height - height * tick / 5
        parts += [
            f'<line x1="{left}" y1="{y}" x2="{left+width}" y2="{y}" class="grid"/>',
            f'<text x="{left-8}" y="{y+4}" text-anchor="end" class="small">{value:.1f}{suffix}</text>',
        ]
    names = list(series)
    group_width = width / len(labels)
    bar_width = min(54, group_width / (len(names) + 1))
    for index, label in enumerate(labels):
        center = left + group_width * (index + 0.5)
        parts.append(f'<text x="{center}" y="{top+height+28}" text-anchor="middle" class="label">{html.escape(label)}</text>')
        for offset, name in enumerate(names):
            value = series[name][index]
            x = center + (offset - (len(names) - 1) / 2) * bar_width - bar_width * 0.42
            bar_height = height * value / maximum
            color = COLORS.get(name, "#0f766e")
            parts.append(f'<rect x="{x}" y="{top+height-bar_height}" width="{bar_width*0.84}" height="{bar_height}" rx="3" fill="{color}"/>')
            parts.append(f'<text x="{x+bar_width*0.42}" y="{top+height-bar_height-7}" text-anchor="middle" class="small">{value:.1f}{suffix}</text>')
    for index, name in enumerate(names):
        color = COLORS.get(name, "#0f766e")
        x = 650 + index * 140
        parts += [
            f'<rect x="{x}" y="72" width="12" height="12" fill="{color}"/>',
            f'<text x="{x+18}" y="83" class="label">{html.escape(name)}</text>',
        ]
    finish_svg(parts, path)


def weekly_chart(path: Path, weekly: dict) -> None:
    parts = svg_start(
        "Weekly LLM latency trend",
        "X axis is actual decision week 1–19; median sum of decision/event LLM latency per persona-seed cell.",
        height=720,
    )
    for panel, scenario in enumerate(SCENARIO_LABELS):
        left, top, width, height = 80, 105 + panel * 290, 860, 210
        values = [
            weekly[(scenario, variant, week)]["latency_ms"] / 1000
            for variant in (APC, MTP)
            for week in range(1, 20)
        ]
        maximum = max(values) * 1.1
        parts.append(f'<text x="{left}" y="{top-12}" class="label">{SCENARIO_LABELS[scenario]}</text>')
        for tick in range(5):
            y = top + height - height * tick / 4
            value = maximum * tick / 4
            parts += [
                f'<line x1="{left}" y1="{y}" x2="{left+width}" y2="{y}" class="grid"/>',
                f'<text x="{left-8}" y="{y+4}" text-anchor="end" class="small">{value:.0f}s</text>',
            ]
        for variant in (APC, MTP):
            points = []
            for week in range(1, 20):
                x = left + width * (week - 1) / 18
                value = weekly[(scenario, variant, week)]["latency_ms"] / 1000
                y = top + height - height * value / maximum
                points.append(f"{x:.1f},{y:.1f}")
                parts.append(f'<circle cx="{x}" cy="{y}" r="2.5" fill="{COLORS[variant]}"/>')
            parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{COLORS[variant]}" stroke-width="2.5"/>')
        for week in range(1, 20):
            x = left + width * (week - 1) / 18
            parts.append(f'<text x="{x}" y="{top+height+18}" text-anchor="middle" class="small">{week}</text>')
    parts += [
        '<rect x="700" y="72" width="12" height="12" fill="#2563eb"/><text x="718" y="83" class="label">APC</text>',
        '<rect x="790" y="72" width="12" height="12" fill="#e11d48"/><text x="808" y="83" class="label">MTP=3</text>',
        '<text x="500" y="700" text-anchor="middle" class="label">Decision week</text>',
    ]
    finish_svg(parts, path)


def paired_effect_chart(path: Path, effects: dict[str, list[float]]) -> None:
    parts = svg_start("Paired campaign effects", "Positive values mean MTP completes the same 76-week cohort faster.")
    left, top, width, height = 120, 110, 780, 280
    minimum, maximum = -5, 35
    zero_x = left + width * (0 - minimum) / (maximum - minimum)
    parts.append(f'<line x1="{zero_x}" y1="{top}" x2="{zero_x}" y2="{top+height}" stroke="#0f172a" stroke-dasharray="4 4"/>')
    for index, (scenario, values) in enumerate(effects.items()):
        y = top + 80 + index * 120
        low, high = bootstrap_ci(values)
        mean = statistics.mean(values)
        x_low = left + width * (low - minimum) / (maximum - minimum)
        x_high = left + width * (high - minimum) / (maximum - minimum)
        x_mean = left + width * (mean - minimum) / (maximum - minimum)
        parts += [
            f'<text x="{left}" y="{y-30}" class="label">{html.escape(SCENARIO_LABELS[scenario])}</text>',
            f'<line x1="{x_low}" y1="{y}" x2="{x_high}" y2="{y}" stroke="#475569" stroke-width="5"/>',
            f'<circle cx="{x_mean}" cy="{y}" r="8" fill="#e11d48"/>',
            f'<text x="{x_mean}" y="{y-13}" text-anchor="middle" class="small">mean {mean:.1f}%</text>',
        ]
        for ordinal, value in enumerate(values):
            x = left + width * (value - minimum) / (maximum - minimum)
            parts.append(f'<circle cx="{x}" cy="{y+18}" r="4" fill="#fda4af"/><text x="{x}" y="{y+36}" text-anchor="middle" class="small">R{ordinal+1}</text>')
    for tick in range(-5, 36, 5):
        x = left + width * (tick - minimum) / (maximum - minimum)
        parts += [
            f'<line x1="{x}" y1="{top+height}" x2="{x}" y2="{top+height+5}" class="axis"/>',
            f'<text x="{x}" y="{top+height+22}" text-anchor="middle" class="small">{tick}%</text>',
        ]
    finish_svg(parts, path)


def heatmap(path: Path, weekly: dict) -> None:
    parts = svg_start("Weekly prompt workload heatmap", "Median input tokens per persona-seed week; rows separate scenario and optimization.")
    left, top = 185, 120
    cell_w, cell_h = 39, 62
    rows = [(scenario, variant) for scenario in SCENARIO_LABELS for variant in (APC, MTP)]
    values = [weekly[(s, v, w)]["input_tokens"] for s, v in rows for w in range(1, 20)]
    low, high = min(values), max(values)
    for row_index, (scenario, variant) in enumerate(rows):
        y = top + row_index * cell_h
        parts.append(f'<text x="{left-12}" y="{y+30}" text-anchor="end" class="small">{SCENARIO_LABELS[scenario]} / {variant}</text>')
        for week in range(1, 20):
            value = weekly[(scenario, variant, week)]["input_tokens"]
            ratio = (value - low) / (high - low or 1)
            red = int(239 - ratio * 190)
            green = int(246 - ratio * 110)
            blue = int(255 - ratio * 30)
            x = left + (week - 1) * cell_w
            parts.append(f'<rect x="{x}" y="{y}" width="{cell_w-2}" height="{cell_h-6}" fill="rgb({red},{green},{blue})"/>')
            parts.append(f'<text x="{x+cell_w/2-1}" y="{y+33}" text-anchor="middle" class="small">{value/1000:.1f}k</text>')
    for week in range(1, 20):
        x = left + (week - 1) * cell_w + cell_w / 2
        parts.append(f'<text x="{x}" y="{top+len(rows)*cell_h+16}" text-anchor="middle" class="small">{week}</text>')
    finish_svg(parts, path)


def quality_chart(path: Path, arms: list[dict], attempts: list[dict]) -> None:
    valid_attempts = defaultdict(int)
    total_attempts = defaultdict(int)
    for attempt in attempts:
        total_attempts[attempt["variant"]] += 1
        valid_attempts[attempt["variant"]] += int(attempt["valid"])
    metrics = {
        "Attempt pass": [valid_attempts[v] / total_attempts[v] * 100 for v in (APC, MTP)],
        "Final valid": [
            statistics.mean(1 - arm["fallback_rate"] for arm in arms if arm["variant"] == v) * 100
            for v in (APC, MTP)
        ],
        "No schema repair": [
            statistics.mean(1 - arm["repair_rate"] for arm in arms if arm["variant"] == v) * 100
            for v in (APC, MTP)
        ],
        "No length finish": [
            statistics.mean(1 - arm["length_finish_rate"] for arm in arms if arm["variant"] == v) * 100
            for v in (APC, MTP)
        ],
    }
    bar_chart(
        path,
        "Quality and stability guardrails",
        "Higher is better. Strict plan requires 100% for every bar; both arms violate repair/length gates.",
        list(metrics),
        {APC: [metrics[label][0] for label in metrics], MTP: [metrics[label][1] for label in metrics]},
        suffix="%",
    )


def write_report(project: Path, root: Path) -> dict[str, Any]:
    arms, attempts = discover(root)
    enrich_arms(project, arms)
    aggregate = aggregate_weekly(arms)
    weekly = aggregate["weekly"]
    charts = root / "charts"
    charts.mkdir(parents=True, exist_ok=True)

    paired = {}
    for scenario in SCENARIO_LABELS:
        values = []
        for repetition in (1, 2, 3):
            pair = {
                arm["variant"]: arm
                for arm in arms
                if arm["scenario"] == scenario and arm["repetition"] == repetition
            }
            values.append((1 - pair[MTP]["wall_seconds"] / pair[APC]["wall_seconds"]) * 100)
        paired[scenario] = values

    throughput_labels = ["Same persona", "Different personas"]
    throughput_series = {
        variant: [
            statistics.mean(
                arm["throughput"]
                for arm in arms
                if arm["variant"] == variant and arm["scenario"] == scenario
            )
            for scenario in SCENARIO_LABELS
        ]
        for variant in (APC, MTP)
    }
    bar_chart(
        charts / "campaign-throughput-by-scenario.svg",
        "Completed decision weeks per wall-clock hour",
        "Each arm contains the same 4 cells and 76 completed weeks; bars are means of 3 repetitions.",
        throughput_labels,
        throughput_series,
        suffix="",
    )

    latency_series = {}
    latency_labels = []
    for scenario in SCENARIO_LABELS:
        for quantile in (0.5, 0.9, 0.95, 0.99):
            latency_labels.append(f"{'Same' if scenario == 'same-persona' else 'Diff'} p{int(quantile*100)}")
    for variant in (APC, MTP):
        values = []
        for scenario in SCENARIO_LABELS:
            latencies = [
                float(call["metadata"].get("latency_ms") or 0) / 1000
                for arm in arms
                if arm["scenario"] == scenario and arm["variant"] == variant
                for call in arm["calls"]
            ]
            values.extend(percentile(latencies, quantile) for quantile in (0.5, 0.9, 0.95, 0.99))
        latency_series[variant] = values
    bar_chart(
        charts / "latency-percentiles.svg",
        "Logical call latency percentiles",
        "Public call latency includes bounded repair attempts; seconds per decision/event logical call.",
        latency_labels,
        latency_series,
        suffix="s",
    )
    weekly_chart(charts / "week-latency-trend.svg", weekly)
    paired_effect_chart(charts / "paired-cell-effects.svg", paired)
    heatmap(charts / "workload-heatmap.svg", weekly)

    mechanism = {
        APC: [
            statistics.mean(arm["cache_hit_rate"] for arm in arms if arm["variant"] == APC and arm["scenario"] == scenario) * 100
            for scenario in SCENARIO_LABELS
        ],
        MTP: [
            statistics.mean(arm["mtp_acceptance_rate"] for arm in arms if arm["variant"] == MTP and arm["scenario"] == scenario) * 100
            for scenario in SCENARIO_LABELS
        ],
    }
    bar_chart(
        charts / "mechanism-utilization.svg",
        "Optimization mechanism utilization",
        "APC bars are cached/query token ratio; MTP bars are accepted/draft speculative token ratio.",
        throughput_labels,
        mechanism,
        suffix="%",
    )

    stage_labels = [
        f"{'Same' if scenario == 'same-persona' else 'Diff'} / {variant}"
        for scenario in SCENARIO_LABELS
        for variant in (APC, MTP)
    ]
    stage = {
        "Input kTok/request": [
            statistics.mean(
                arm["input_tokens"] / arm["physical_requests"] / 1000
                for arm in arms
                if arm["variant"] == variant and arm["scenario"] == scenario
            )
            for scenario in SCENARIO_LABELS
            for variant in (APC, MTP)
        ],
        "Output kTok/request": [
            statistics.mean(
                arm["output_tokens"] / arm["physical_requests"] / 1000
                for arm in arms
                if arm["variant"] == variant and arm["scenario"] == scenario
            )
            for scenario in SCENARIO_LABELS
            for variant in (APC, MTP)
        ],
    }
    bar_chart(
        charts / "stage-decomposition.svg",
        "Stage workload proxy",
        "Mean input/output tokens per physical request. TTFT/TPOT sweep was stopped and is not inferred.",
        stage_labels,
        stage,
        suffix="k",
    )

    gpu_series = {
        variant: [
            statistics.mean(
                arm["gpu"]["energy_wh"] for arm in arms
                if arm["variant"] == variant and arm["scenario"] == scenario
            )
            for scenario in SCENARIO_LABELS
        ]
        for variant in (APC, MTP)
    }
    bar_chart(
        charts / "gpu-energy.svg",
        "GPU energy per complete campaign arm",
        "Integrated GPU 0 power at 1-second sampling; each arm completes 76 decision weeks.",
        throughput_labels,
        gpu_series,
        suffix="Wh",
    )
    quality_chart(charts / "quality-guardrails.svg", arms, attempts)

    scenario_stats = {}
    for scenario, values in paired.items():
        low, high = bootstrap_ci(values)
        scenario_stats[scenario] = {
            "mtp_speedup_percent_by_repetition": [round(value, 3) for value in values],
            "mean_mtp_speedup_percent": round(statistics.mean(values), 3),
            "paired_bootstrap_95_ci_percent": [round(low, 3), round(high, 3)],
            "all_repetitions_favor_mtp": all(value > 0 for value in values),
        }

    invalid = [
        {
            "repetition": attempt["repetition"],
            "scenario": attempt["scenario"],
            "variant": attempt["variant"],
            "arm_name": attempt["arm_name"],
            "status": attempt["result"].get("status"),
            "cells": attempt["result"].get("cells"),
            "wall_time_seconds": attempt["timing"].get("wall_time_seconds"),
        }
        for attempt in attempts
        if not attempt["valid"]
    ]
    for failure in invalid:
        scenario_short = (
            "same" if failure["scenario"] == "same-persona" else "different"
        )
        variant_short = "mtp3" if failure["variant"] == MTP else "apc"
        campaign_dir = (
            project
            / "reports"
            / "persona-campaigns"
            / f"inference-ab-r{failure['repetition']}-{scenario_short}-{variant_short}"
        )
        run_summary_path = campaign_dir / "campaign_run_summary.json"
        if run_summary_path.exists():
            run_summary = json.loads(run_summary_path.read_text(encoding="utf-8"))
            failure["campaign_id"] = run_summary.get("campaign_id")
            failure["status_counts"] = run_summary.get("status_counts")
        cell_errors = []
        for cell_path in sorted((campaign_dir / "cells").glob("*/cell_result.json")):
            cell = json.loads(cell_path.read_text(encoding="utf-8"))
            if cell.get("state") != "completed" or cell.get("error"):
                cell_errors.append(
                    {
                        "cell_id": cell.get("request", {}).get("cell_id"),
                        "persona": cell.get("request", {}).get("persona"),
                        "state": cell.get("state"),
                        "error": cell.get("error"),
                    }
                )
        failure["cell_errors"] = cell_errors
    summary = {
        "schema_version": "inference-ab-summary-v1",
        "status": "completed_long_horizon_with_aborted_diagnostics",
        "truth_label": "local-vllm-real-godot",
        "performance_winner": MTP,
        "governed_default_decision": "no-go",
        "decision_reason": (
            "MTP is consistently faster in valid long campaigns, but strict quality gates "
            "are not satisfied: MTP had one rejected arm and both variants rely heavily on "
            "bounded schema repair/length-limited thinking."
        ),
        "scenario_stats": scenario_stats,
        "valid_arms": 12,
        "completed_weeks": sum(arm["weeks"] for arm in arms),
        "valid_cells": 48,
        "invalid_attempts": invalid,
        "aborted_diagnostics": {
            "path": "diagnostics/frozen-trace/apc-only/c1/aborted.json",
            "included_in_conclusion": False,
        },
        "trace_capture": {
            "records": 299,
            "sha256": hashlib.sha256(
                (project / "reports/inference-ab/fixtures/persona-chat-trace.jsonl").read_bytes()
            ).hexdigest(),
            "included_as_performance_result": False,
        },
        "arms": [
            {
                key: arm[key]
                for key in (
                    "repetition",
                    "scenario",
                    "variant",
                    "arm_name",
                    "wall_seconds",
                    "weeks",
                    "throughput",
                    "input_tokens",
                    "output_tokens",
                    "physical_requests",
                    "repair_rate",
                    "fallback_rate",
                    "provider_error_rate",
                    "cache_hit_rate",
                    "mtp_acceptance_rate",
                    "length_finish_rate",
                    "gpu",
                )
            }
            for arm in arms
        ],
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with (root / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "repetition", "scenario", "variant", "wall_seconds", "weeks", "throughput",
            "input_tokens", "output_tokens", "physical_requests", "repair_rate",
            "cache_hit_rate", "mtp_acceptance_rate", "length_finish_rate", "energy_wh",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for arm in arms:
            writer.writerow({
                **{key: arm[key] for key in fields if key != "energy_wh"},
                "energy_wh": arm["gpu"]["energy_wh"],
            })

    with (root / "requests.jsonl").open("w", encoding="utf-8") as handle:
        for arm in arms:
            for call in arm["calls"]:
                handle.write(json.dumps({
                    "repetition": arm["repetition"],
                    "scenario": arm["scenario"],
                    "variant": arm["variant"],
                    **call,
                }, sort_keys=True) + "\n")

    with (root / "server-metrics.jsonl").open("w", encoding="utf-8") as handle:
        for arm in arms:
            handle.write(json.dumps({
                "repetition": arm["repetition"],
                "scenario": arm["scenario"],
                "variant": arm["variant"],
                **arm["prom"],
            }, sort_keys=True) + "\n")

    with (root / "gpu-metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = ["repetition", "scenario", "variant", "samples", "mean_util", "mean_power", "mean_memory_mib", "mean_clock_mhz", "energy_wh"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for arm in arms:
            writer.writerow({"repetition": arm["repetition"], "scenario": arm["scenario"], "variant": arm["variant"], **arm["gpu"]})

    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project, text=True).strip()
    manifest = {
        "schema_version": "inference-ab-report-manifest-v1",
        "experiment_root": str(root.relative_to(project)),
        "generator_revision": revision,
        "valid_arm_count": 12,
        "invalid_attempt_count": len(invalid),
        "completed_weeks": summary["completed_weeks"],
        "charts": sorted(path.name for path in charts.glob("*.svg")),
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    chart_order = [
        "week-latency-trend.svg",
        "campaign-throughput-by-scenario.svg",
        "paired-cell-effects.svg",
        "latency-percentiles.svg",
        "mechanism-utilization.svg",
        "workload-heatmap.svg",
        "stage-decomposition.svg",
        "quality-guardrails.svg",
        "gpu-energy.svg",
    ]
    arm_rows = "\n".join(
        f"<tr><td>R{arm['repetition']}</td><td>{html.escape(SCENARIO_LABELS[arm['scenario']])}</td><td>{arm['variant']}</td><td>{arm['wall_seconds']:.2f}</td><td>{arm['throughput']:.1f}</td><td>{arm['cache_hit_rate']*100:.1f}%</td><td>{arm['mtp_acceptance_rate']*100:.1f}%</td><td>{arm['repair_rate']*100:.1f}%</td></tr>"
        for arm in arms
    )
    report = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>APC vs MTP=3 A/B report</title>
<style>body{{font-family:Inter,Arial,sans-serif;margin:32px auto;max-width:1180px;color:#172033}}.callout{{padding:18px;border-left:5px solid #e11d48;background:#fff1f2}}img{{width:100%;border:1px solid #e2e8f0;margin:16px 0 32px}}table{{border-collapse:collapse;width:100%}}th,td{{padding:8px;border-bottom:1px solid #e2e8f0;text-align:right}}th:nth-child(-n+3),td:nth-child(-n+3){{text-align:left}}code{{background:#f1f5f9;padding:2px 5px}}</style></head>
<body><h1>APC vs MTP=3：本地 vLLM × Docker Godot 长程 A/B</h1>
<div class="callout"><strong>结论：</strong>MTP=3 是性能赢家，但不是受控默认赢家。两个场景的 3 次重复全部更快；同时 MTP 有一次被拒绝的整组运行，而且两臂都大量触发 schema repair / length-limited thinking，违反预设质量门禁。因此默认配置保持 <code>APC</code>，下一步应先修复结构化输出路径，再复测。</div>
<p>完整证据：12 个有效 arm、48 个完整 persona cells、{summary['completed_weeks']} 个周决策。停止后的 frozen replay 不进入结论。主趋势图的 X 轴是实际 week 1–19。</p>
<h2>配对结果</h2>
<ul><li>同 persona / 4 seeds：MTP 平均快 {scenario_stats['same-persona']['mean_mtp_speedup_percent']:.1f}%（3 次：{', '.join(str(v) for v in scenario_stats['same-persona']['mtp_speedup_percent_by_repetition'])}%）。</li>
<li>4 personas / same seed：MTP 平均快 {scenario_stats['different-personas']['mean_mtp_speedup_percent']:.1f}%（3 次：{', '.join(str(v) for v in scenario_stats['different-personas']['mtp_speedup_percent_by_repetition'])}%）。</li></ul>
{''.join(f'<img src="charts/{name}" alt="{name}">' for name in chart_order)}
<h2>每个有效 arm</h2><table><thead><tr><th>Rep</th><th>Scenario</th><th>Variant</th><th>Wall s</th><th>Weeks/h</th><th>APC hit</th><th>MTP accept</th><th>Repair</th></tr></thead><tbody>{arm_rows}</tbody></table>
<h2>证据限制</h2><p>TTFT/TPOT diagnostic sweep 按用户指示停止，因此 stage-decomposition 只展示 token workload proxy，不把未完成 sweep 推断成阶段性能。置信区间是对 3 个配对 repetition 的 bootstrap；样本很小，应与每次原始效果同时阅读。</p>
</body></html>"""
    (root / "comparison.html").write_text(report, encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-root", type=Path, required=True)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    root = args.experiment_root.resolve()
    summary = write_report(project, root)
    print(json.dumps(summary["scenario_stats"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
