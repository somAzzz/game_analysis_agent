"""Value / balance reasonableness analyzer.

Inputs: ``action_pick_rates.csv`` + ``event_trigger_rates.csv`` +
``choice_pick_rates.csv`` (computed by :mod:`game_analysis_agent.analytics`).

The analyzer is statistical, not LLM-driven — its output is meant to be
consumed by the ``value_reviewer`` agent which adds narrative explanation
on top. Findings are emitted as :class:`game_analysis_agent.schemas.ValueFinding`
rows written to ``value_report.json``.

Heuristics:

* **Dominant action**: pick_rate_per_run > 0.80  → "必选".
* **Dead action**: pick_rate_per_run < 0.05  → "无人选".
* **Dominant choice** (per event): rate_per_event > 0.85 → "该选项被碾压".
* **Far-from-balanced outcome**: ending distribution within a single
  policy is > 90% on one ending → "玩法单一".
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from game_analysis_agent.schemas import ValueFinding

DOMINANT_PICK_RATE = 0.80
DEAD_PICK_RATE = 0.05
DOMINANT_CHOICE_RATE = 0.85
ENDINGLE_DOMINANCE = 0.90


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def analyze_values(
    *,
    action_csv: Path | None = None,
    event_csv: Path | None = None,
    choice_csv: Path | None = None,
    ending_csv: Path | None = None,
    dominant_pick: float = DOMINANT_PICK_RATE,
    dead_pick: float = DEAD_PICK_RATE,
    dominant_choice: float = DOMINANT_CHOICE_RATE,
    ending_dominance: float = ENDINGLE_DOMINANCE,
) -> list[ValueFinding]:
    """Return a list of :class:`ValueFinding` rows."""

    findings: list[ValueFinding] = []
    counter = _FindingCounter()

    if action_csv is not None:
        for row in load_csv(action_csv):
            policy = row.get("policy", "")
            action_id = row.get("action_id", "")
            try:
                rate = float(row.get("rate_per_run", 0.0))
                count = int(row.get("count", 0))
            except (TypeError, ValueError):
                continue
            if rate >= dominant_pick and count >= 5:
                findings.append(
                    ValueFinding(
                        finding_id=counter.next("action_dominant"),
                        scope="action",
                        target_id=f"{policy}:{action_id}",
                        severity="warning",
                        metric="rate_per_run",
                        value=rate,
                        threshold=dominant_pick,
                        description=(
                            f"Action `{action_id}` (policy={policy}) is picked "
                            f"{rate:.1%} of runs — probable 'must-pick'."
                        ),
                    )
                )
            elif rate <= dead_pick and count >= 0:
                findings.append(
                    ValueFinding(
                        finding_id=counter.next("action_dead"),
                        scope="action",
                        target_id=f"{policy}:{action_id}",
                        severity="info",
                        metric="rate_per_run",
                        value=rate,
                        threshold=dead_pick,
                        description=(
                            f"Action `{action_id}` (policy={policy}) was picked "
                            f"{rate:.1%} of runs — likely 'no value'."
                        ),
                    )
                )

    if choice_csv is not None:
        by_event: dict[tuple[str, str], list[tuple[str, int, float]]] = defaultdict(list)
        for row in load_csv(choice_csv):
            policy = row.get("policy", "")
            event_id = row.get("event_id", "")
            choice_id = row.get("choice_id", "")
            try:
                rate = float(row.get("rate_per_event", 0.0))
                count = int(row.get("count", 0))
            except (TypeError, ValueError):
                continue
            if not event_id or not choice_id:
                continue
            by_event[(policy, event_id)].append((choice_id, count, rate))
        for (policy, event_id), entries in by_event.items():
            if not entries:
                continue
            entries.sort(key=lambda item: item[2], reverse=True)
            top_choice, top_count, top_rate = entries[0]
            if top_rate >= dominant_choice and top_count >= 3:
                findings.append(
                    ValueFinding(
                        finding_id=counter.next("choice_dominant"),
                        scope="choice",
                        target_id=f"{policy}:{event_id}:{top_choice}",
                        severity="warning",
                        metric="rate_per_event",
                        value=top_rate,
                        threshold=dominant_choice,
                        description=(
                            f"Choice `{top_choice}` dominates event `{event_id}` "
                            f"({top_rate:.1%} of triggers)."
                        ),
                    )
                )

    if event_csv is not None:
        for row in load_csv(event_csv):
            policy = row.get("policy", "")
            event_id = row.get("event_id", "")
            try:
                rate = float(row.get("rate_per_run", 0.0))
            except (TypeError, ValueError):
                continue
            if rate <= 0.005:
                findings.append(
                    ValueFinding(
                        finding_id=counter.next("event_rare"),
                        scope="event",
                        target_id=f"{policy}:{event_id}",
                        severity="info",
                        metric="rate_per_run",
                        value=rate,
                        threshold=0.005,
                        description=(
                            f"Event `{event_id}` only triggered in "
                            f"{rate:.2%} of runs — likely unreachable."
                        ),
                    )
                )

    if ending_csv is not None:
        by_policy: dict[str, list[tuple[str, int, float]]] = defaultdict(list)
        for row in load_csv(ending_csv):
            policy = row.get("policy", "")
            ending_id = row.get("ending_id", "")
            try:
                rate = float(row.get("rate", 0.0))
                count = int(row.get("count", 0))
            except (TypeError, ValueError):
                continue
            by_policy[policy].append((ending_id, count, rate))
        for policy, endings in by_policy.items():
            endings.sort(key=lambda item: item[2], reverse=True)
            if not endings:
                continue
            top = endings[0]
            if top[2] >= ending_dominance and top[1] >= 5:
                findings.append(
                    ValueFinding(
                        finding_id=counter.next("ending_dominant"),
                        scope="ending",
                        target_id=f"{policy}:{top[0]}",
                        severity="warning",
                        metric="rate",
                        value=top[2],
                        threshold=ending_dominance,
                        description=(
                            f"Policy `{policy}` reaches `{top[0]}` in "
                            f"{top[2]:.1%} of runs — play style feels single-track."
                        ),
                    )
                )

    return findings


class _FindingCounter:
    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)

    def next(self, prefix: str) -> str:
        self._counters[prefix] += 1
        return f"{prefix}-{self._counters[prefix]:04d}"


def write_value_report(
    findings: Iterable[ValueFinding],
    path: Path,
    *,
    meta: dict[str, Any] | None = None,
) -> int:
    findings_list = list(findings)
    payload: dict[str, Any] = {
        "finding_count": len(findings_list),
        "by_kind": _group_findings(findings_list),
        "findings": [finding.model_dump(mode="json") for finding in findings_list],
    }
    if meta is not None:
        payload["meta"] = meta
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(findings_list)


def _group_findings(findings: list[ValueFinding]) -> dict[str, int]:
    grouped: dict[str, int] = defaultdict(int)
    for finding in findings:
        key = finding.finding_id.rsplit("-", 1)[0]
        grouped[key] += 1
    return dict(sorted(grouped.items()))


def analyze_and_write(report_dir: Path) -> list[ValueFinding]:
    findings = analyze_values(
        action_csv=report_dir / "action_pick_rates.csv",
        event_csv=report_dir / "event_trigger_rates.csv",
        choice_csv=report_dir / "choice_pick_rates.csv",
        ending_csv=report_dir / "ending_distribution.csv",
    )
    write_value_report(findings, report_dir / "value_report.json")
    return findings


__all__ = [
    "DEAD_PICK_RATE",
    "DOMINANT_CHOICE_RATE",
    "DOMINANT_PICK_RATE",
    "ENDINGLE_DOMINANCE",
    "analyze_and_write",
    "analyze_values",
    "write_value_report",
]
