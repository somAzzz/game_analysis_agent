"""Event graph QA agent: emit reachability + broken-chain report."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from game_analysis_agent.agents.base import Agent


class EventGraphAgent(Agent):
    name = "event_graph"
    default_output_files = ("event_graph_report.md",)
    default_temperature = 0.1

    def build_user_prompt(self, report_dir: Path, context: dict[str, Any]) -> str:
        path = self.prompts_root / f"{self.name}_user.md"
        template = path.read_text(encoding="utf-8")
        return template.replace(
            "{{UNTRIGGERED_EVENTS}}",
            build_untriggered_block_from_dir(report_dir),
        )


def build_untriggered_block_from_dir(report_dir: Path) -> str:
    """Build a deterministic reachability hint block for the LLM prompt."""
    raw_runs = _load_jsonl(report_dir / "raw_runs.jsonl")
    event_graph = _load_json(report_dir / "event_graph.json")
    return build_untriggered_block(raw_runs, event_graph)


def build_untriggered_block(
    raw_runs: list[dict[str, Any]],
    event_graph: dict[str, Any],
    *,
    rare_threshold: int = 0,
) -> str:
    """Summarize events that never or rarely trigger in the observed runs."""
    events = event_graph.get("events") if isinstance(event_graph, dict) else None
    if not isinstance(events, list) or not events:
        return "## Untriggered Events\n\nNo event_graph.json events available.\n"

    trigger_counts = _count_event_triggers(raw_runs)
    lines = ["## Untriggered Events", ""]
    rows: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        count = trigger_counts.get(event_id, 0)
        if count > rare_threshold:
            continue
        trigger = event.get("trigger") or event.get("conditions") or {}
        rows.append(
            "- "
            + f"`{event_id}`: triggers={count}; "
            + f"trigger={_compact_json(trigger)}; "
            + f"hint={_missing_reason_hint(raw_runs, trigger)}"
        )

    if not rows:
        lines.append("No untriggered events found in the current raw runs.")
    else:
        lines.extend(rows)
    lines.append("")
    return "\n".join(lines)


def _count_event_triggers(raw_runs: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for run in raw_runs:
        for week in run.get("weekly_log", []) or []:
            if not isinstance(week, dict):
                continue
            event_id = str(
                week.get("triggered_event_id") or week.get("event_id") or ""
            ).strip()
            if event_id:
                counts[event_id] += 1
    return counts


def _missing_reason_hint(raw_runs: list[dict[str, Any]], trigger: Any) -> str:
    if not isinstance(trigger, dict) or not trigger:
        return "no trigger metadata to inspect"
    flag = trigger.get("flag") or trigger.get("required_flag")
    if isinstance(flag, str) and flag:
        seen = any(_run_has_flag(run, flag) for run in raw_runs)
        return f"required flag `{flag}` {'appears' if seen else 'never appears'} in raw runs"
    metric = trigger.get("metric") or trigger.get("stat")
    threshold = trigger.get("min") or trigger.get("gte") or trigger.get("value")
    if isinstance(metric, str) and isinstance(threshold, (int, float)):
        reached = any(_run_reaches_metric(run, metric, float(threshold)) for run in raw_runs)
        return f"metric `{metric}` {'reaches' if reached else 'never reaches'} {threshold}"
    week = trigger.get("week")
    if isinstance(week, (int, float)):
        return f"fixed week trigger at week {int(week)}; check branch prerequisites"
    return "trigger shape is custom; inspect conditions manually"


def _run_has_flag(run: dict[str, Any], flag: str) -> bool:
    states = [run.get("final_state") or {}]
    states.extend(
        week.get("after_state") or week.get("state") or {}
        for week in run.get("weekly_log", []) or []
        if isinstance(week, dict)
    )
    for state in states:
        if isinstance(state, dict):
            flags = state.get("flags")
            if isinstance(flags, dict) and bool(flags.get(flag)):
                return True
    flags = run.get("flags")
    return isinstance(flags, dict) and bool(flags.get(flag))


def _run_reaches_metric(run: dict[str, Any], metric: str, threshold: float) -> bool:
    for week in run.get("weekly_log", []) or []:
        if not isinstance(week, dict):
            continue
        state = week.get("after_state") or week.get("state") or {}
        if (
            isinstance(state, dict)
            and isinstance(state.get(metric), (int, float))
            and float(state[metric]) >= threshold
        ):
            return True
    final_state = run.get("final_state") or {}
    return (
        isinstance(final_state, dict)
        and isinstance(final_state.get(metric), (int, float))
        and float(final_state[metric]) >= threshold
    )


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


__all__ = [
    "EventGraphAgent",
    "build_untriggered_block",
    "build_untriggered_block_from_dir",
]
