"""Content QA agent: emit a table of content issues per event."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from game_analysis_agent.agents.base import Agent


class ContentQAAgent(Agent):
    name = "content_qa"
    default_output_files = ("content_issues.md",)
    default_temperature = 0.15

    def build_user_prompt(self, report_dir: Path, context: dict[str, Any]) -> str:
        template = self.read_prompt_template("user")
        return template.replace(
            "{{CHOICE_STRUCTURE_FINDINGS}}",
            render_choice_structure_findings(score_choice_structure_from_dir(report_dir)),
        )


def score_choice_structure_from_dir(report_dir: Path) -> list[dict[str, Any]]:
    event_graph = _load_json(report_dir / "event_graph.json")
    return score_choice_structure(event_graph)


def score_choice_structure(event_graph: dict[str, Any]) -> list[dict[str, Any]]:
    """Return deterministic content-structure findings for event choices."""
    events = event_graph.get("events") if isinstance(event_graph, dict) else None
    if not isinstance(events, list):
        return []

    findings: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        choices = event.get("choices") or []
        if not event_id or not isinstance(choices, list) or not choices:
            continue

        normalized_texts = [
            str(choice.get("text") or "").strip().lower()
            for choice in choices
            if isinstance(choice, dict)
        ]
        if len(normalized_texts) != len(set(normalized_texts)):
            findings.append(_finding(event_id, "duplicate_choice_text", "warning"))

        effect_vectors = []
        all_positive = True
        missing_cost_count = 0
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            merged = _choice_effects(choice)
            if not merged:
                missing_cost_count += 1
            if any(value < 0 for value in merged.values()):
                all_positive = False
            effect_vectors.append(merged)

        if choices and all_positive and any(effect_vectors):
            findings.append(_finding(event_id, "all_choices_positive", "warning"))
        if missing_cost_count == len(choices):
            findings.append(_finding(event_id, "missing_failure_cost", "warning"))
        if _effects_too_similar(effect_vectors):
            findings.append(_finding(event_id, "choice_effects_too_similar", "info"))

    return findings


def render_choice_structure_findings(findings: list[dict[str, Any]]) -> str:
    lines = ["## Choice Structure Findings", ""]
    if not findings:
        lines.append("No deterministic choice-structure issues found.")
        lines.append("")
        return "\n".join(lines)
    lines.append("event_id | issue_type | severity | explanation")
    lines.append("--- | --- | --- | ---")
    for finding in findings:
        lines.append(
            f"{finding['event_id']} | {finding['issue_type']} | "
            f"{finding['severity']} | {finding['explanation']}"
        )
    lines.append("")
    return "\n".join(lines)


def _finding(event_id: str, issue_type: str, severity: str) -> dict[str, Any]:
    explanations = {
        "duplicate_choice_text": "Two or more choices have identical visible text.",
        "all_choices_positive": "All choices appear to carry non-negative effects.",
        "missing_failure_cost": "No choice exposes an explicit effect or cost.",
        "choice_effects_too_similar": "Choice effect vectors are nearly identical.",
    }
    return {
        "event_id": event_id,
        "issue_type": issue_type,
        "severity": severity,
        "explanation": explanations.get(issue_type, issue_type),
    }


def _choice_effects(choice: dict[str, Any]) -> dict[str, float]:
    merged: dict[str, float] = {}
    for key in ("effects", "success_effects", "failure_effects", "stat_effects", "costs"):
        payload = choice.get(key)
        if not isinstance(payload, dict):
            continue
        sign = -1.0 if key == "costs" else 1.0
        for metric, value in payload.items():
            if isinstance(value, (int, float)):
                merged[str(metric)] = merged.get(str(metric), 0.0) + sign * float(value)
    return merged


def _effects_too_similar(vectors: list[dict[str, float]]) -> bool:
    non_empty = [vector for vector in vectors if vector]
    if len(non_empty) < 2:
        return False
    keys = sorted({key for vector in non_empty for key in vector})
    tuples = [tuple(round(vector.get(key, 0.0), 3) for key in keys) for vector in non_empty]
    return len(set(tuples)) == 1


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


__all__ = [
    "ContentQAAgent",
    "render_choice_structure_findings",
    "score_choice_structure",
    "score_choice_structure_from_dir",
]
