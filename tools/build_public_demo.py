#!/usr/bin/env python3
"""Build a sanitized public demo dataset for the React dashboard.

The private ``reports/`` tree can contain raw game event text, full event
graphs, replay evidence, and complete playthrough traces. This script keeps the
public dashboard useful without publishing that full gameplay surface:

* aggregate counts, ending distributions, anomaly counts, and metric trends are
  derived from real reports;
* issue ids, action ids, event ids, finding text, and anomaly evidence are
  generalized;
* the decision graph is a small illustrative mock, not the real event graph.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS = ROOT / "reports"
DEFAULT_OUT = ROOT / "frontend" / "public-demo"

METRICS_TO_KEEP = (
    "stress",
    "hunger",
    "money",
    "academic_progress",
    "social",
    "visa_progress",
)

ENDING_ALIASES = {
    "academic_failure": "Outcome A - academic risk",
    "burnout_pause": "Outcome B - recovery pause",
    "career_launch": "Outcome C - career route",
    "cashflow_collapse": "Outcome D - cash pressure",
    "visa_timeout": "Outcome E - admin deadline",
    "stable_semester": "Outcome F - stable semester",
}

ACTION_BUCKETS = (
    "study action",
    "income action",
    "admin action",
    "social action",
    "recovery action",
    "living-cost action",
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _slug_parts(issue_id: str) -> dict[str, str]:
    parts = issue_id.split("-")
    out = {"scenario": "sample", "difficulty": "normal", "policy": "mixed"}
    for policy in ("balanced", "study", "work", "social", "admin", "slacker", "random"):
        if policy in parts:
            out["policy"] = policy
    for difficulty in ("normal", "realistic"):
        if difficulty in parts:
            out["difficulty"] = difficulty
    if "low_money_start" in issue_id:
        out["scenario"] = "low money start"
    elif "high_stress_start" in issue_id:
        out["scenario"] = "high stress start"
    elif "default_first_semester" in issue_id:
        out["scenario"] = "first semester"
    elif issue_id.startswith("final-") or issue_id.startswith("fix-verify-"):
        out["scenario"] = issue_id.replace("final-", "").replace("fix-verify-", "")
    return out


def _ending_label(raw: str) -> str:
    return ENDING_ALIASES.get(raw, "Outcome X - other")


def _severity_rank(severity: str) -> int:
    return {"critical": 3, "error": 2, "warning": 1, "info": 0}.get(severity, 0)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _sanitize_card(card: dict[str, Any], idx: int) -> dict[str, Any]:
    parts = _slug_parts(str(card.get("id", "")))
    public_id = f"{card.get('kind', 'issue')}-sample-{idx:02d}"
    top = card.get("top_ending")
    return {
        "kind": card.get("kind", "balance"),
        "id": public_id,
        "slug": f"{card.get('kind', 'balance')}/{public_id}",
        "title": f"{parts['scenario'].title()} / {parts['policy']} / {parts['difficulty']}",
        "subtitle": (
            f"Sanitized aggregate from a real {parts['scenario']} test cell. "
            "Raw event text and full rule graph are withheld."
        ),
        "total_runs": _safe_int(card.get("total_runs")),
        "top_ending": None
        if not isinstance(top, dict)
        else {
            "policy": parts["policy"],
            "ending_id": _ending_label(str(top.get("ending_id", ""))),
            "count": _safe_int(top.get("count")),
            "rate": _safe_float(top.get("rate")),
        },
        "anomaly_total": _safe_int(card.get("anomaly_total")),
        "severity": card.get("severity", "info"),
        "has_decision_graph": idx == 1 and card.get("kind") == "balance",
        "scenario": parts["scenario"],
        "difficulty": parts["difficulty"],
        "policy": parts["policy"],
    }


def _sanitize_endings(rows: list[dict[str, Any]], policy: str) -> list[dict[str, str]]:
    out = []
    for row in rows[:8]:
        out.append(
            {
                "policy": policy,
                "ending_id": _ending_label(str(row.get("ending_id", ""))),
                "count": str(_safe_int(row.get("count"))),
                "rate": f"{_safe_float(row.get('rate')):.4f}",
            }
        )
    return out


def _sanitize_actions(rows: list[dict[str, Any]], policy: str) -> list[dict[str, str]]:
    out = []
    for idx, row in enumerate(rows[:10]):
        out.append(
            {
                "policy": policy,
                "action_id": ACTION_BUCKETS[idx % len(ACTION_BUCKETS)],
                "count": str(_safe_int(row.get("count"))),
                "rate_per_run": f"{_safe_float(row.get('rate_per_run')):.4f}",
            }
        )
    return out


def _sanitize_weekly(series: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    kept: dict[str, list[dict[str, Any]]] = {}
    for metric in METRICS_TO_KEEP:
        points = series.get(metric, [])
        kept[metric] = [
            {
                "week": _safe_int(p.get("week")),
                "mean": _safe_float(p.get("mean")),
                "p10": _safe_float(p.get("p10")),
                "p90": _safe_float(p.get("p90")),
            }
            for p in points
        ][:24]
    return {k: v for k, v in kept.items() if v}


def _sanitize_anomalies(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (str(row.get("kind", "unknown")), str(row.get("severity", "info")))
        counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (_severity_rank(item[0][1]), item[1]), reverse=True)
    return [
        {
            "kind": kind,
            "severity": severity,
            "run_id": idx + 1,
            "week": 0,
            "policy": "sanitized",
            "message": f"{count} occurrence(s) in the private run set. Replay evidence withheld.",
        }
        for idx, ((kind, severity), count) in enumerate(ranked[:12])
    ]


def _sanitize_findings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for idx, row in enumerate(rows[:8]):
        metric = str(row.get("metric", "metric"))
        severity = str(row.get("severity", "info"))
        out.append(
            {
                "finding_id": f"public-finding-{idx + 1:02d}",
                "scope": str(row.get("scope", "aggregate")),
                "target_id": f"sanitized-target-{idx + 1:02d}",
                "severity": severity,
                "metric": metric,
                "value": _safe_float(row.get("value")),
                "threshold": _safe_float(row.get("threshold")),
                "description": (
                    f"Real aggregate signal on {metric}; private action/event identifiers "
                    "were generalized for the public demo."
                ),
            }
        )
    return out


def _agent_summary(issue: dict[str, Any], card: dict[str, Any]) -> str:
    top = card.get("top_ending") or {}
    endings = issue.get("endings", [])
    return "\n".join(
        [
            "# Public Review Summary",
            "",
            "This public report is derived from a real test cell, but raw traces, full event text, and complete rule graphs are not included.",
            "",
            f"- Runs represented: **{card.get('total_runs', 0)}**",
            f"- Top public outcome: **{top.get('ending_id', 'n/a')}**",
            f"- Sanitized anomaly groups: **{len(issue.get('anomalies', []))}**",
            f"- Ending rows shown: **{len(endings)}**",
            "",
            "Use the private report bundle for replay-level debugging. This static site is meant for portfolio and stakeholder review.",
        ]
    )


def _sanitize_issue(issue: dict[str, Any], card: dict[str, Any], source_id: str) -> dict[str, Any]:
    policy = str(card.get("policy", "mixed"))
    public_id = str(card["id"])
    sanitized = {
        "kind": card["kind"],
        "id": public_id,
        "slug": f"{card['kind']}/{public_id}",
        "report_dir": "public-demo/sanitized",
        "summary": {
            "total_runs": card["total_runs"],
            "scenario": card["scenario"],
            "difficulty": card["difficulty"],
            "policy": policy,
            "source": "sanitized aggregate from real local reports",
            "privacy": "raw runs, replay evidence, and full gameplay graph withheld",
        },
        "endings": _sanitize_endings(issue.get("endings", []), policy),
        "actions": _sanitize_actions(issue.get("actions", []), policy),
        "events": [],
        "choices": [],
        "weekly_series": _sanitize_weekly(issue.get("weekly_series", {})),
        "anomalies": _sanitize_anomalies(issue.get("anomalies", [])),
        "value_findings": _sanitize_findings(issue.get("value_findings", [])),
        "route_findings": {
            "groups": [],
            "crisis_response": [],
            "ending_contradictions": [],
            "route_separation": [],
        },
        "agents": [{"label": "public review summary", "file": "public_review.md", "bytes": "0"}],
        "agent_markdown": {},
        "gate_report": issue.get("gate_report"),
        "coverage_report": {
            "public_demo": True,
            "source_issue_id_hash": abs(hash(source_id)) % 1000000,
        },
        "raw_runs_count": card["total_runs"],
        "public_demo": True,
        "public_notice": "Sanitized public demo: complete game rules and raw playthroughs are withheld.",
        "source_summary": {
            "source_kind": card["kind"],
            "source_policy": policy,
            "source_scenario": card["scenario"],
            "source_difficulty": card["difficulty"],
        },
    }
    sanitized["agent_markdown"]["public_review"] = _agent_summary(sanitized, card)
    sanitized["agents"][0]["bytes"] = str(len(sanitized["agent_markdown"]["public_review"]))
    return sanitized


def _mock_decision_graph(issue_id: str) -> dict[str, Any]:
    events = [
        ("phase-1", 1, "Arrival pressure", "fixed"),
        ("phase-2", 3, "Budget fork", "conditional"),
        ("phase-3", 6, "Social support check", "conditional"),
        ("phase-4", 9, "Study load spike", "random"),
        ("phase-5", 13, "Admin deadline", "fixed"),
        ("phase-6", 17, "Recovery or collapse", "conditional"),
    ]
    graph_events = []
    weekly_log = []
    for idx, (event_id, week, title, event_type) in enumerate(events):
        graph_events.append(
            {
                "id": event_id,
                "title": title,
                "body": "Public demo node. Real game text is withheld.",
                "event_type": event_type,
                "trigger": {"week": week},
                "source_order": idx,
                "choices": [
                    {
                        "text": "Stabilize short-term risk",
                        "success_effects": {"stress": -3, "money": -1, "social": 1},
                    },
                    {
                        "text": "Invest in long-term progress",
                        "success_effects": {"academic_progress": 4, "stress": 2, "money": -2},
                    },
                    {
                        "text": "Ask the support network",
                        "success_effects": {"social": 3, "stress": -1, "money": 1},
                    },
                ],
            }
        )
        choice_index = idx % 3
        weekly_log.append(
            {
                "week": week,
                "triggered_event_id": event_id,
                "event_choice_id": f"{event_id}.choice_{choice_index + 1:02d}",
                "choice_index": choice_index,
                "selected_action_ids": ["public-action-a", "public-action-b"],
                "after_state": {
                    "stress": 35 + idx * 7,
                    "money": 700 - idx * 120,
                    "social": 20 + idx * 5,
                    "academic_progress": 12 + idx * 9,
                },
            }
        )
    return {
        "issue_id": issue_id,
        "run_id": 0,
        "policy": "public-demo",
        "scenario": "sanitized",
        "seed": 42,
        "max_weeks": 20,
        "final_ending_id": "Outcome B - recovery pause",
        "public_demo": True,
        "public_notice": "Illustrative graph only. The private full event graph is not published.",
        "run": {
            "run_id": 0,
            "policy": "public-demo",
            "seed": 42,
            "weekly_log": weekly_log,
        },
        "event_graph": {"events": graph_events},
    }


def build_public_demo(reports: Path, out: Path, max_issues: int = 12) -> dict[str, Any]:
    front = _load_json(reports / "manifest.json")
    issue_cards = []
    issue_sources = []
    selected = [
        card
        for card in front.get("issues", [])
        if card.get("kind") in {"balance", "boundary", "play"}
    ][:max_issues]
    if not selected:
        raise SystemExit(f"No issues found in {reports / 'manifest.json'}")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    for idx, source_card in enumerate(selected, start=1):
        card = _sanitize_card(source_card, idx)
        src_path = reports / "browse" / str(source_card["kind"]) / str(source_card["id"]) / "manifest.json"
        if not src_path.exists():
            continue
        issue = _sanitize_issue(_load_json(src_path), card, str(source_card["id"]))
        _write_json(out / "browse" / card["kind"] / card["id"] / "manifest.json", issue)
        issue_cards.append(card)
        issue_sources.append({"kind": card["kind"], "id": card["id"], "path": f"{card['kind']}/{card['id']}"})

    if issue_cards:
        issue_cards[0]["has_decision_graph"] = True
        _write_json(
            out / "browse" / "decision_graph" / issue_cards[0]["id"] / "0" / "manifest.json",
            _mock_decision_graph(issue_cards[0]["id"]),
        )

    source_counts = front.get("counts", {})
    public_front = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "public_demo": True,
        "public_notice": (
            "This dashboard uses real aggregate report data, but private raw runs, "
            "complete event graphs, and gameplay text are withheld."
        ),
        "source_counts": source_counts,
        "counts": {
            "issues": len(issue_cards),
            "decision_graphs": 1 if issue_cards else 0,
            "total_runs": sum(_safe_int(c.get("total_runs")) for c in issue_cards),
            "total_anomalies": sum(_safe_int(c.get("anomaly_total")) for c in issue_cards),
            "total_critical": sum(1 for c in issue_cards if c.get("severity") == "critical"),
        },
        "issues": issue_cards,
        "issues_index": issue_sources,
    }
    _write_json(out / "manifest.json", public_front)
    return public_front


def copy_to_public(public_demo: Path, public: Path) -> None:
    public.mkdir(parents=True, exist_ok=True)
    for rel in ("manifest.json", "browse"):
        target = public / rel
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        src = public_demo / rel
        if src.is_dir():
            shutil.copytree(src, target)
        elif src.exists():
            shutil.copy2(src, target)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", type=Path, default=DEFAULT_REPORTS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-issues", type=int, default=12)
    parser.add_argument(
        "--copy-to-public",
        action="store_true",
        help="Also mirror the sanitized dataset into frontend/public for Vite.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    front = build_public_demo(args.reports, args.out, args.max_issues)
    if args.copy_to_public:
        copy_to_public(args.out, ROOT / "frontend" / "public")
    print(
        f"Wrote {args.out} with {front['counts']['issues']} issue(s), "
        f"{front['counts']['total_runs']} public run aggregates."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
