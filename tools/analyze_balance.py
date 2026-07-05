#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

METRICS = [
    "money",
    "energy",
    "stress",
    "loneliness",
    "academic",
    "german",
    "social",
    "admin",
    "career",
]


def usage() -> None:
    print("Usage: python3 tools/analyze_balance.py <raw_runs.jsonl> <out_dir>")


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * ratio)))
    return ordered[index]


def load_runs(path: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                runs.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_no}: {exc}") from exc
    return runs


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def analyze(runs: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    runs_by_policy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        runs_by_policy[str(run.get("policy", "unknown"))].append(run)

    ending_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    choice_rows: list[dict[str, Any]] = []
    weekly_values: dict[tuple[str, int, str], list[float]] = defaultdict(list)

    top_events: Counter[str] = Counter()
    anomalies: list[str] = []

    for policy, policy_runs in sorted(runs_by_policy.items()):
        ending_counter = Counter(str(run.get("ending_id", "unknown")) for run in policy_runs)
        for ending_id, count in sorted(ending_counter.items()):
            ending_rows.append(
                {
                    "policy": policy,
                    "ending_id": ending_id,
                    "count": count,
                    "rate": round(count / len(policy_runs), 6),
                }
            )

        action_counter: Counter[str] = Counter()
        event_counter: Counter[str] = Counter()
        choice_counter: Counter[tuple[str, str]] = Counter()
        event_choice_totals: Counter[str] = Counter()

        for run in policy_runs:
            for week in run.get("weekly_log", []):
                for action_id in week.get("actions", []):
                    action_counter[str(action_id)] += 1

                event_id = str(week.get("event_id", "") or "")
                choice_id = str(week.get("choice_id", "") or "")
                if event_id:
                    event_counter[event_id] += 1
                    top_events[event_id] += 1
                if event_id and choice_id:
                    choice_counter[(event_id, choice_id)] += 1
                    event_choice_totals[event_id] += 1

                state = week.get("state", {})
                week_no = int(week.get("week", state.get("week", 0)) or 0)
                for metric in METRICS:
                    if metric in state and isinstance(state[metric], (int, float)):
                        weekly_values[(policy, week_no, metric)].append(float(state[metric]))

        for action_id, count in sorted(action_counter.items()):
            action_rows.append(
                {
                    "policy": policy,
                    "action_id": action_id,
                    "count": count,
                    "rate_per_run": round(count / len(policy_runs), 6),
                }
            )

        for event_id, count in sorted(event_counter.items()):
            event_rows.append(
                {
                    "policy": policy,
                    "event_id": event_id,
                    "count": count,
                    "rate_per_run": round(count / len(policy_runs), 6),
                }
            )

        for (event_id, choice_id), count in sorted(choice_counter.items()):
            total = event_choice_totals[event_id]
            choice_rows.append(
                {
                    "policy": policy,
                    "event_id": event_id,
                    "choice_id": choice_id,
                    "count": count,
                    "rate_per_event": round(count / total, 6) if total else 0,
                }
            )

        dominant_actions = [
            action_id for action_id, count in action_counter.items() if count / len(policy_runs) > 0.6
        ]
        if dominant_actions:
            anomalies.append(
                f"- `{policy}` has high-frequency actions: {', '.join(sorted(dominant_actions))}."
            )

    weekly_rows: list[dict[str, Any]] = []
    for (policy, week_no, metric), values in sorted(weekly_values.items()):
        weekly_rows.append(
            {
                "policy": policy,
                "week": week_no,
                "metric": metric,
                "mean": round(statistics.fmean(values), 4),
                "median": round(statistics.median(values), 4),
                "p10": round(percentile(values, 0.1), 4),
                "p90": round(percentile(values, 0.9), 4),
                "min": round(min(values), 4),
                "max": round(max(values), 4),
            }
        )

    write_csv(out_dir / "ending_distribution.csv", ["policy", "ending_id", "count", "rate"], ending_rows)
    write_csv(out_dir / "weekly_stats.csv", ["policy", "week", "metric", "mean", "median", "p10", "p90", "min", "max"], weekly_rows)
    write_csv(out_dir / "action_pick_rates.csv", ["policy", "action_id", "count", "rate_per_run"], action_rows)
    write_csv(out_dir / "event_trigger_rates.csv", ["policy", "event_id", "count", "rate_per_run"], event_rows)
    write_csv(out_dir / "choice_pick_rates.csv", ["policy", "event_id", "choice_id", "count", "rate_per_event"], choice_rows)

    summary = {
        "total_runs": len(runs),
        "policies": {policy: len(policy_runs) for policy, policy_runs in sorted(runs_by_policy.items())},
        "top_events": dict(top_events.most_common(20)),
        "generated_files": [
            "ending_distribution.csv",
            "weekly_stats.csv",
            "action_pick_rates.csv",
            "event_trigger_rates.csv",
            "choice_pick_rates.csv",
            "anomaly_report.md",
        ],
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if not anomalies:
        anomalies.append("- No automatic anomalies detected. Review distribution thresholds manually.")
    (out_dir / "anomaly_report.md").write_text(
        "# Anomaly Report\n\n" + "\n".join(anomalies) + "\n", encoding="utf-8"
    )


def main() -> int:
    if len(sys.argv) != 3:
        usage()
        return 2
    raw_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    if not raw_path.exists():
        print(f"Missing raw file: {raw_path}", file=sys.stderr)
        return 1
    runs = load_runs(raw_path)
    analyze(runs, out_dir)
    print(f"Analysis written to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
