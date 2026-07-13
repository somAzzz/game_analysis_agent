#!/usr/bin/env python3
"""Emit static JSON manifests consumed by the React frontend.

The React app under ``frontend/`` reads three kinds of JSON:

* ``reports/manifest.json``            — top-level index (every issue + KPIs)
* ``reports/browse/<kind>/<id>/manifest.json`` — single-issue data (endings,
  actions, anomalies, value findings, route findings, agent markdown bodies,
  weekly stats for sparklines, gate report)
* ``reports/browse/decision_graph/<run>/<id>/manifest.json`` — one run's
  decision graph (event graph + triggered events + diagnostics)

This script walks ``reports/`` once and writes all three. It is meant to
run *after* the simulation/analyse agents (i.e. as the final step of
``build_dashboard.py all``) so the React side has fresh data on every
build.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS = ROOT / "reports"


def _load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _display_path_for(path: Path, root: Path) -> str:
    """Render a path relative to ``root`` when possible, else absolute."""
    try:
        return str(path.relative_to(root))
    except (ValueError, RuntimeError):
        return str(path)


def _scan_agents(report_dir: Path) -> list[dict[str, str]]:
    """List the agent markdown files that actually exist + their byte size."""
    agents: list[dict[str, str]] = []
    for name in (
        "agent_diagnosis.md",
        "tuning_proposal.md",
        "content_issues.md",
        "event_graph_report.md",
        "bug_diagnosis.md",
        "boundary_report.md",
        "value_review.md",
        "bugs_summary.md",
    ):
        path = report_dir / name
        if path.exists():
            agents.append(
                {
                    "label": name.replace("_", " ").replace(".md", ""),
                    "file": name,
                    "bytes": str(path.stat().st_size),
                }
            )
    return agents


def _issue_card_payload(report_dir: Path, kind: str, issue_id: str) -> dict | None:
    """Build a slim payload for the front-page issue shelf."""
    summary = _load_json(report_dir / "summary.json")
    if not summary and not (report_dir / "raw_runs.jsonl").exists():
        return None
    raw_runs = _load_jsonl(report_dir / "raw_runs.jsonl")
    boundary_runs = _load_jsonl(report_dir / "boundary_runs.jsonl")
    anomalies = _load_jsonl(report_dir / "anomalies.jsonl")
    boundary_anomalies = []
    for r in boundary_runs:
        boundary_anomalies.extend(r.get("anomalies", []) or [])
    endings_rows = _load_csv(report_dir / "ending_distribution.csv")
    endings = [
        {
            "policy": row.get("policy", ""),
            "ending_id": row.get("ending_id", ""),
            "count": int(float(row.get("count", 0) or 0)),
            "rate": float(row.get("rate", 0) or 0),
        }
        for row in endings_rows
    ]
    top_ending = max(endings, key=lambda r: r["rate"]) if endings else None
    total_runs = (
        (summary or {}).get("total_runs")
        or len(raw_runs)
        or len(boundary_runs)
        or 0
    )
    anomaly_total = len(anomalies) + len(boundary_anomalies)
    severity = "info"
    for a in anomalies + boundary_anomalies:
        s = str(a.get("severity", ""))
        if s == "critical":
            severity = "critical"
            break
        if s == "warning" and severity != "critical":
            severity = "warning"
    return {
        "kind": kind,
        "id": issue_id,
        "slug": f"{kind}/{issue_id}",
        "title": issue_id.replace("-", " "),
        "subtitle": (summary or {}).get("scenario", "")
        or (summary or {}).get("top_events", {})
        and ", ".join(list((summary or {}).get("top_events", {}).keys())[:3])
        or "",
        "total_runs": int(total_runs or 0),
        "top_ending": top_ending,
        "anomaly_total": anomaly_total,
        "severity": severity,
        "has_decision_graph": (report_dir / "raw_runs.jsonl").exists()
        and (report_dir / "event_graph.json").exists(),
    }


def _emit_issue_manifest(report_dir: Path, kind: str, issue_id: str) -> dict | None:
    """Build the per-issue manifest consumed by the IssuePage route."""
    summary = _load_json(report_dir / "summary.json") or {}
    raw_runs = _load_jsonl(report_dir / "raw_runs.jsonl")
    anomalies = _load_jsonl(report_dir / "anomalies.jsonl")
    endings = _load_csv(report_dir / "ending_distribution.csv")
    actions = _load_csv(report_dir / "action_pick_rates.csv")
    weekly_rows = _load_csv(report_dir / "weekly_stats.csv")
    events_rows = _load_csv(report_dir / "event_trigger_rates.csv")
    choices_rows = _load_csv(report_dir / "choice_pick_rates.csv")
    value = _load_json(report_dir / "value_report.json") or {}
    route = _load_json(report_dir / "route_report.json") or {}
    gate = _load_json(report_dir / "gate_report.json")
    coverage = _load_json(report_dir / "coverage_report.json")

    # Convert weekly_stats CSV rows into a compact per-metric time series.
    weekly_series: dict[str, list[dict]] = {}
    for row in weekly_rows:
        try:
            week = int(row.get("week", 0))
        except (TypeError, ValueError):
            continue
        metric = row.get("metric", "")
        try:
            mean = float(row.get("mean", 0) or 0)
            p10 = float(row.get("p10", 0) or 0)
            p90 = float(row.get("p90", 0) or 0)
        except (TypeError, ValueError):
            continue
        weekly_series.setdefault(metric, []).append(
            {"week": week, "mean": mean, "p10": p10, "p90": p90}
        )
    for series in weekly_series.values():
        series.sort(key=lambda p: p["week"])

    return {
        "kind": kind,
        "id": issue_id,
        "slug": f"{kind}/{issue_id}",
        "report_dir": _display_path_for(report_dir, ROOT),
        "summary": summary,
        "endings": endings,
        "actions": actions,
        "events": events_rows,
        "choices": choices_rows,
        "weekly_series": weekly_series,
        "anomalies": anomalies,
        "value_findings": value.get("findings", []) or [],
        "route_findings": {
            "groups": route.get("groups", []),
            "crisis_response": route.get("crisis_response", []),
            "ending_contradictions": route.get("ending_contradictions", []),
            "route_separation": route.get("route_separation", []),
        },
        "agents": _scan_agents(report_dir),
        "agent_markdown": {
            "agent_diagnosis": _load_text(report_dir / "agent_diagnosis.md"),
            "tuning_proposal": _load_text(report_dir / "tuning_proposal.md"),
            "bug_diagnosis": _load_text(report_dir / "bug_diagnosis.md"),
            "value_review": _load_text(report_dir / "value_review.md"),
            "boundary_report": _load_text(report_dir / "boundary_report.md"),
            "content_issues": _load_text(report_dir / "content_issues.md"),
            "event_graph_report": _load_text(report_dir / "event_graph_report.md"),
            "bugs_summary": _load_text(report_dir / "bugs_summary.md"),
        },
        "gate_report": gate,
        "coverage_report": coverage,
        "raw_runs_count": len(raw_runs),
    }


def _emit_decision_graph_manifest(
    report_dir: Path,
    issue_id: str,
    run_id: int = 0,
) -> dict | None:
    """Build the per-decision-graph manifest consumed by the graph route."""
    if not (report_dir / "raw_runs.jsonl").exists():
        return None
    if not (report_dir / "event_graph.json").exists():
        return None
    runs = _load_jsonl(report_dir / "raw_runs.jsonl")
    if not runs:
        return None
    event_graph = _load_json(report_dir / "event_graph.json") or {}
    target = next(
        (r for r in runs if int(r.get("run_id", -1)) == run_id),
        runs[0],
    )
    return {
        "issue_id": issue_id,
        "run_id": int(target.get("run_id", 0)),
        "policy": str(target.get("policy", "")),
        "scenario": str(target.get("scenario", "")),
        "seed": target.get("seed"),
        "max_weeks": int(target.get("max_weeks", 20) or 20),
        "final_ending_id": str(target.get("final_ending_id") or ""),
        "run": target,
        "event_graph": event_graph,
    }


def emit_all(reports: Path = DEFAULT_REPORTS) -> dict:
    """Walk ``reports/`` and emit every manifest. Returns a summary dict."""
    reports = reports.resolve()
    if not reports.exists():
        print(f"reports dir does not exist: {reports}", file=sys.stderr)
        return {"issues": 0, "graphs": 0}

    # Front page manifest.
    issue_cards: list[dict] = []
    browse_root = reports / "browse"
    browse_root.mkdir(parents=True, exist_ok=True)

    issues_meta: list[dict] = []
    graph_count = 0

    balance_root = reports / "balance"
    if balance_root.exists():
        for child in sorted(balance_root.iterdir()):
            if not child.is_dir():
                continue
            card = _issue_card_payload(child, "balance", child.name)
            if card:
                issue_cards.append(card)
            manifest = _emit_issue_manifest(child, "balance", child.name)
            if manifest:
                (browse_root / "balance" / child.name).mkdir(parents=True, exist_ok=True)
                (browse_root / "balance" / child.name / "manifest.json").write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                issues_meta.append(
                    {"kind": "balance", "id": child.name, "path": f"balance/{child.name}"}
                )
                # Decision graph (if applicable)
                dg = _emit_decision_graph_manifest(child, child.name, 0)
                if dg:
                    dg_dir = browse_root / "decision_graph" / child.name / "0"
                    dg_dir.mkdir(parents=True, exist_ok=True)
                    (dg_dir / "manifest.json").write_text(
                        json.dumps(dg, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    graph_count += 1
                    (browse_root / "decision_graph" / child.name / "0").joinpath("_diagnostics.json").write_text(
                        json.dumps(
                            {
                                "issue_id": child.name,
                                "events_in_graph": len(dg["event_graph"].get("events", [])),
                                "triggered_count": len(dg["run"].get("weekly_log", []) or []),
                                "policy": dg["policy"],
                                "scenario": dg["scenario"],
                                "ending_id": dg["final_ending_id"],
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )

    boundary_root = reports / "boundary"
    if boundary_root.exists():
        for child in sorted(boundary_root.iterdir()):
            if not child.is_dir():
                continue
            card = _issue_card_payload(child, "boundary", child.name)
            if card:
                issue_cards.append(card)
            manifest = _emit_issue_manifest(child, "boundary", child.name)
            if manifest:
                (browse_root / "boundary" / child.name).mkdir(parents=True, exist_ok=True)
                (browse_root / "boundary" / child.name / "manifest.json").write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                issues_meta.append(
                    {"kind": "boundary", "id": child.name, "path": f"boundary/{child.name}"}
                )

    play_root = reports / "play"
    if play_root.exists():
        for child in sorted(play_root.iterdir()):
            if not child.is_dir():
                continue
            card = _issue_card_payload(child, "play", child.name)
            if card:
                issue_cards.append(card)
            manifest = _emit_issue_manifest(child, "play", child.name)
            if manifest:
                (browse_root / "play" / child.name).mkdir(parents=True, exist_ok=True)
                (browse_root / "play" / child.name / "manifest.json").write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                issues_meta.append(
                    {"kind": "play", "id": child.name, "path": f"play/{child.name}"}
                )

    # Front page manifest
    total_runs = sum(card["total_runs"] for card in issue_cards)
    total_anomalies = sum(card["anomaly_total"] for card in issue_cards)
    total_critical = sum(
        1
        for card in issue_cards
        if card["severity"] == "critical"
    )
    front = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "counts": {
            "issues": len(issue_cards),
            "decision_graphs": graph_count,
            "total_runs": total_runs,
            "total_anomalies": total_anomalies,
            "total_critical": total_critical,
        },
        "issues": issue_cards,
        "issues_index": issues_meta,
    }
    (reports / "manifest.json").write_text(
        json.dumps(front, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {reports / 'manifest.json'} ({len(issue_cards)} issues, {graph_count} decision graphs)")
    return front


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="emit_manifest")
    parser.add_argument(
        "--reports",
        type=Path,
        default=DEFAULT_REPORTS,
        help="Root reports directory (defaults to ./reports).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="If set, also copy the front-page manifest to this path "
        "(e.g. frontend/public/manifest.json for Vite).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    emit_all(args.reports)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        # Re-emit just the front-page manifest to the alternate path
        # so Vite can `import manifest from "/manifest.json"`.
        front = json.loads((args.reports / "manifest.json").read_text(encoding="utf-8"))
        args.out.write_text(
            json.dumps(front, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Copied manifest → {args.out}")
    return 0


__all__ = ["build_parser", "emit_all", "main"]


if __name__ == "__main__":
    raise SystemExit(main())