#!/usr/bin/env python3
"""Build an editorial-style HTML dashboard for ``game_analysis_agent``.

The dashboard treats every report directory as an *issue* of a print
magazine — a cover page, a numbered KPI strip, typeset columns of the
seven agents' markdown reports, and (when present) a playthrough spine.

Outputs:
  * ``reports/index.html``                    — front page (recent issues)
  * ``reports/browse/<run_id>/index.html``    — one magazine issue per run
  * ``reports/browse/<extreme>/index.html``   — one issue per boundary extreme
  * ``reports/play/<persona>/index.html``     — one issue per playthrough

Run:
  python3 tools/build_dashboard.py
  python3 tools/build_dashboard.py --reports reports --out reports/browse

No third-party dependencies. Markdown is rendered by a tiny subset
parser inside this file (headings, paragraphs, lists, blockquotes, code
fences, tables, bold/italic/inline-code). Everything is inlined into
each HTML file so the output works from a static ``file://`` URL.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS = ROOT / "reports"
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# ---------------------------------------------------------------------------
# Tiny markdown renderer (subset)
# ---------------------------------------------------------------------------


_INLINE_PATTERNS = [
    (re.compile(r"\*\*(?=\S)([^*]+?)(?<=\S)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"(?<=\s)\*(?=\S)([^*\n]+?)(?<=\S)\*(?=\s|[\.,;!?])"), r"<em>\1</em>"),
    (re.compile(r"`([^`\n]+)`"), r"<code>\1</code>"),
]


def _apply_inline(text: str) -> str:
    out = html.escape(text)
    for pattern, repl in _INLINE_PATTERNS:
        out = pattern.sub(repl, out)
    return out


def render_markdown(source: str) -> str:
    """Render the subset of markdown we actually use in agent reports."""
    if not source:
        return ""
    lines = source.splitlines()
    out: list[str] = []
    in_code = False
    code_lang = ""
    code_buf: list[str] = []
    in_table = False
    table_buf: list[list[str]] = []
    list_stack: list[str] = []  # tag: "ul" | "ol"
    para_buf: list[str] = []

    def flush_paragraph() -> None:
        if not para_buf:
            return
        joined = " ".join(para_buf).strip()
        if joined:
            out.append(f"<p>{_apply_inline(joined)}</p>")
        para_buf.clear()

    def close_lists() -> None:
        while list_stack:
            out.append(f"</{list_stack.pop()}>")

    def render_table(buf: list[list[str]]) -> None:
        if len(buf) < 2:
            return
        head = buf[0]
        body = buf[2:]  # skip separator row
        out.append("<table class='md-table'>")
        out.append("<thead><tr>")
        for cell in head:
            out.append(f"<th>{_apply_inline(cell.strip())}</th>")
        out.append("</tr></thead>")
        out.append("<tbody>")
        for row in body:
            if not any(cell.strip() for cell in row):
                continue
            out.append("<tr>")
            for cell in row:
                out.append(f"<td>{_apply_inline(cell.strip())}</td>")
            out.append("</tr>")
        out.append("</tbody></table>")

    for line in lines:
        if in_code:
            if line.strip().startswith("```"):
                out.append(
                    f"<pre class='md-code'><code data-lang='{code_lang}'>"
                    f"{html.escape(chr(10).join(code_buf))}</code></pre>"
                )
                code_buf = []
                code_lang = ""
                in_code = False
            else:
                code_buf.append(line)
            continue

        stripped = line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            close_lists()
            in_code = True
            code_lang = stripped[3:].strip()
            continue

        # Table row detection: pipe-delimited, separator present
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c for c in stripped.strip("|").split("|")]
            table_buf.append(cells)
            in_table = True
            continue
        elif in_table:
            flush_paragraph()
            close_lists()
            render_table(table_buf)
            table_buf = []
            in_table = False

        if not stripped:
            flush_paragraph()
            close_lists()
            continue

        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            close_lists()
            level = len(heading.group(1))
            content = heading.group(2).strip()
            # numbered footnote-style ref detection: "1. text" or "1) text"
            out.append(f"<h{level} class='md-h{level}'>{_apply_inline(content)}</h{level}>")
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            close_lists()
            content = stripped.lstrip(">").strip()
            out.append(f"<blockquote class='md-quote'>{_apply_inline(content)}</blockquote>")
            continue

        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        ordered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if bullet or ordered:
            flush_paragraph()
            tag = "ol" if ordered else "ul"
            if list_stack and list_stack[-1] != tag:
                out.append(f"</{list_stack.pop()}>")
            if not list_stack:
                out.append(f"<{tag} class='md-list'>")
                list_stack.append(tag)
            content = (bullet or ordered).group(1).strip()
            out.append(f"<li>{_apply_inline(content)}</li>")
            continue

        close_lists()
        para_buf.append(stripped)

    flush_paragraph()
    close_lists()
    if in_table:
        render_table(table_buf)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Run aggregation
# ---------------------------------------------------------------------------


@dataclass
class WeeklyPoint:
    week: int
    metric: str
    mean: float
    p10: float = 0.0
    p90: float = 0.0


@dataclass
class Issue:
    issue_id: str
    issue_kind: str  # "balance" | "boundary" | "play"
    slug: str  # relative path under reports/, used for drilling in
    title: str
    subtitle: str
    byline: str  # e.g. "GENEV A. VANCE · 2026-07-06"
    scenarios: list[str] = field(default_factory=list)
    policies: list[str] = field(default_factory=list)
    total_runs: int = 0
    endings: list[dict[str, str]] = field(default_factory=list)
    top_actions: list[dict[str, str]] = field(default_factory=list)
    anomalies: list[dict] = field(default_factory=list)
    anomaly_counts: dict[str, int] = field(default_factory=dict)
    value_findings: list[dict] = field(default_factory=list)
    route_findings: list[dict] = field(default_factory=list)
    weekly_series: list[WeeklyPoint] = field(default_factory=list)
    weekly_metrics: list[str] = field(default_factory=list)
    agents: list[dict[str, str]] = field(default_factory=list)
    bug_diagnosis_md: str = ""
    boundary_report_md: str = ""
    value_review_md: str = ""
    agent_diagnosis_md: str = ""
    tuning_proposal_md: str = ""
    content_issues_md: str = ""
    event_graph_report_md: str = ""
    bugs_summary_md: str = ""
    gate_report: dict | None = None
    coverage_report: dict | None = None
    playthrough: list[dict] = field(default_factory=list)
    playthrough_summary_md: str = ""
    raw_runs_count: int = 0
    manifest: dict | None = None


def _weekly_series_from_csv(rows: list[dict[str, str]]) -> tuple[list[WeeklyPoint], list[str]]:
    series: list[WeeklyPoint] = []
    metrics: set[str] = set()
    for row in rows:
        try:
            week = int(row.get("week", 0))
        except (TypeError, ValueError):
            continue
        metric = row.get("metric", "")
        try:
            mean = float(row.get("mean", 0.0))
            p10 = float(row.get("p10", 0.0))
            p90 = float(row.get("p90", 0.0))
        except (TypeError, ValueError):
            continue
        metrics.add(metric)
        series.append(WeeklyPoint(week=week, metric=metric, mean=mean, p10=p10, p90=p90))
    return series, sorted(metrics)


_AGENT_OUTPUT_FILES = (
    "agent_diagnosis.md",
    "tuning_proposal.md",
    "content_issues.md",
    "event_graph_report.md",
    "bug_diagnosis.md",
    "boundary_report.md",
    "value_review.md",
    "bugs_summary.md",
)


def _scan_agents(report_dir: Path) -> list[dict[str, str]]:
    """List the agent markdown files that actually exist + their byte size."""
    agents: list[dict[str, str]] = []
    for name in _AGENT_OUTPUT_FILES:
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


def _aggregate_balance_issue(report_dir: Path, slug: str) -> Issue | None:
    summary = _load_json(report_dir / "summary.json")
    if not summary and not (report_dir / "raw_runs.jsonl").exists():
        return None
    name = report_dir.name

    endings_rows = _load_csv(report_dir / "ending_distribution.csv")
    endings_pretty = []
    for row in sorted(
        endings_rows, key=lambda r: float(r.get("rate", 0) or 0), reverse=True
    )[:6]:
        endings_pretty.append(
            {
                "policy": row.get("policy", ""),
                "ending_id": row.get("ending_id", ""),
                "count": row.get("count", "0"),
                "rate": f"{float(row.get('rate', 0) or 0):.3f}",
            }
        )

    actions_rows = _load_csv(report_dir / "action_pick_rates.csv")
    actions_pretty = []
    for row in sorted(
        actions_rows, key=lambda r: float(r.get("rate_per_run", 0) or 0), reverse=True
    )[:8]:
        actions_pretty.append(
            {
                "policy": row.get("policy", ""),
                "action_id": row.get("action_id", ""),
                "count": row.get("count", "0"),
                "rate_per_run": f"{float(row.get('rate_per_run', 0) or 0):.3f}",
            }
        )

    anomalies = _load_jsonl(report_dir / "anomalies.jsonl")
    severity_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    for a in anomalies:
        severity_counts[str(a.get("severity", "info"))] += 1
        kind_counts[str(a.get("kind", "unknown"))] += 1

    weekly_rows = _load_csv(report_dir / "weekly_stats.csv")
    weekly, weekly_metrics = _weekly_series_from_csv(weekly_rows)

    value = _load_json(report_dir / "value_report.json") or {}
    value_findings = value.get("findings", []) or []
    route = _load_json(report_dir / "route_report.json") or {}
    route_findings = (
        route.get("groups", [])
        + route.get("crisis_response", [])
        + route.get("ending_contradictions", [])
        + route.get("route_separation", [])
    )

    raw_runs = _load_jsonl(report_dir / "raw_runs.jsonl")

    return Issue(
        issue_id=name,
        issue_kind="balance",
        slug=slug,
        title=_title_for(name, summary),
        subtitle=_subtitle_for_balance(summary),
        byline=_byline_now(),
        scenarios=_scenarios(summary, raw_runs),
        policies=_policies(summary, raw_runs),
        total_runs=int((summary or {}).get("total_runs") or len(raw_runs)),
        endings=endings_pretty,
        top_actions=actions_pretty,
        anomalies=anomalies,
        anomaly_counts=dict(kind_counts),
        value_findings=value_findings,
        route_findings=route_findings,
        weekly_series=weekly,
        weekly_metrics=weekly_metrics,
        agents=_scan_agents(report_dir),
        bug_diagnosis_md=_load_text(report_dir / "bug_diagnosis.md"),
        boundary_report_md="",
        value_review_md=_load_text(report_dir / "value_review.md"),
        agent_diagnosis_md=_load_text(report_dir / "agent_diagnosis.md"),
        tuning_proposal_md=_load_text(report_dir / "tuning_proposal.md"),
        content_issues_md=_load_text(report_dir / "content_issues.md"),
        event_graph_report_md=_load_text(report_dir / "event_graph_report.md"),
        bugs_summary_md=_load_text(report_dir / "bugs_summary.md"),
        gate_report=_load_json(report_dir / "gate_report.json"),
        coverage_report=_load_json(report_dir / "coverage_report.json"),
        raw_runs_count=len(raw_runs),
        manifest=_load_json(report_dir / "report_manifest.json"),
    )


def _aggregate_boundary_issue(report_dir: Path, slug: str) -> Issue | None:
    boundary_runs = _load_jsonl(report_dir / "boundary_runs.jsonl")
    if not boundary_runs:
        return None
    name = report_dir.name
    extreme = name.rsplit("-", 1)[-1] if "-" in name else name
    by_extreme_counts: Counter[str] = Counter()
    ending_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    anomalies: list[dict] = []
    for run in boundary_runs:
        ext = str(run.get("extreme", "unknown"))
        by_extreme_counts[ext] += 1
        ending = str(
            run.get("final_ending_id") or run.get("ending_id") or "unknown"
        )
        ending_counts[ending] += 1
        for a in run.get("anomalies", []) or []:
            anomalies.append(a)
            severity_counts[str(a.get("severity") or a.get("kind", "info"))] += 1
            kind_counts[str(a.get("kind", "unknown"))] += 1
    return Issue(
        issue_id=name,
        issue_kind="boundary",
        slug=slug,
        title=f"Boundary probe · {extreme}",
        subtitle=(
            f"{len(boundary_runs)} runs across "
            f"{len(by_extreme_counts)} extreme scenarii; top ending "
            f"`{ending_counts.most_common(1)[0][0]}`"
            if ending_counts
            else f"{len(boundary_runs)} runs across {len(by_extreme_counts)} extremes"
        ),
        byline=_byline_now(),
        scenarios=sorted(by_extreme_counts.keys()),
        policies=sorted({str(r.get("policy", "")) for r in boundary_runs}),
        total_runs=len(boundary_runs),
        anomalies=anomalies,
        anomaly_counts=dict(kind_counts),
        agents=_scan_agents(report_dir),
        bug_diagnosis_md="",
        boundary_report_md=_load_text(report_dir / "boundary_report.md"),
        value_review_md=_load_text(report_dir / "value_review.md"),
        bugs_summary_md=_load_text(report_dir / "bugs_summary.md"),
        raw_runs_count=len(boundary_runs),
        manifest=_load_json(report_dir / "report_manifest.json"),
    )


def _aggregate_play_issue(report_dir: Path, slug: str) -> Issue | None:
    raw_runs_path = report_dir / "raw_runs.jsonl"
    if not raw_runs_path.exists() and not (report_dir / "playthrough_summary.md").exists():
        return None
    raw_runs = _load_jsonl(raw_runs_path)
    name = report_dir.name
    return Issue(
        issue_id=name,
        issue_kind="play",
        slug=slug,
        title=f"Playthrough · {name}",
        subtitle=f"{len(raw_runs)} interactive runs",
        byline=_byline_now(),
        policies=sorted({str(r.get("policy", "")) for r in raw_runs}),
        total_runs=len(raw_runs),
        playthrough=raw_runs,
        playthrough_summary_md=_load_text(report_dir / "playthrough_summary.md"),
        agents=_scan_agents(report_dir),
        raw_runs_count=len(raw_runs),
        manifest=_load_json(report_dir / "report_manifest.json"),
    )


def _title_for(name: str, summary: dict | None) -> str:
    summary = summary or {}
    parts = name.split("-")
    if len(parts) >= 4 and parts[0] == "full" and parts[1].isdigit():
        date = "-".join(parts[1:4])
        return f"The {date[:4]} cohort — {parts[-2]} / {parts[-1]}"
    return name.replace("-", " ")


def _subtitle_for_balance(summary: dict | None) -> str:
    summary = summary or {}
    total = summary.get("total_runs") or 0
    top_events = list((summary.get("top_events") or {}).items())[:3]
    head = f"{total} runs · "
    if top_events:
        names = ", ".join(name for name, _ in top_events)
        head += f"top events: {names}"
    return head.rstrip(", ")


def _scenarios(summary: dict | None, raw_runs: list[dict]) -> list[str]:
    scenarios = {str(r.get("scenario", "")) for r in raw_runs if r.get("scenario")}
    return sorted(s for s in scenarios if s)


def _policies(summary: dict | None, raw_runs: list[dict]) -> list[str]:
    if summary and isinstance(summary.get("policies"), dict):
        return sorted(summary["policies"].keys())
    return sorted({str(r.get("policy", "")) for r in raw_runs if r.get("policy")})


def _byline_now() -> str:
    return f"GAME ANALYSIS AGENT · {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M UTC')}"


# ---------------------------------------------------------------------------
# Issues discovery
# ---------------------------------------------------------------------------


def _discover_issues(reports: Path) -> list[Issue]:
    issues: list[Issue] = []
    balance_root = reports / "balance"
    if balance_root.exists():
        for child in sorted(balance_root.iterdir()):
            if child.is_dir():
                issue = _aggregate_balance_issue(
                    child, f"balance/{child.name}"
                )
                if issue:
                    issues.append(issue)
    boundary_root = reports / "boundary"
    if boundary_root.exists():
        for child in sorted(boundary_root.iterdir()):
            if child.is_dir():
                issue = _aggregate_boundary_issue(
                    child, f"boundary/{child.name}"
                )
                if issue:
                    issues.append(issue)
    play_root = reports / "play"
    if play_root.exists():
        for child in sorted(play_root.iterdir()):
            if child.is_dir():
                issue = _aggregate_play_issue(child, f"play/{child.name}")
                if issue:
                    issues.append(issue)
    return issues


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------


_CSS = r"""
@import url("https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght,SOFT,WONK@9..144,300..900,0..100,0..1&family=Newsreader:opsz,wght@6..72,300..700&family=IBM+Plex+Mono:wght@300;400;500;600&display=swap");

:root {
  --paper: #F4EFE6;
  --paper-deep: #ECE5D6;
  --ink: #1F1B16;
  --ink-soft: #38322A;
  --rule: #D9D2C5;
  --muted: #8B847A;
  --accent: #C8553D;
  --accent-deep: #8B2A1B;
  --forest: #3B5F4E;
  --warn: #B97C29;
  --critical: #7B1F1F;
  --serif: "Fraunces", "Newsreader", Georgia, serif;
  --body: "Newsreader", Georgia, serif;
  --mono: "IBM Plex Mono", ui-monospace, monospace;
}

* { box-sizing: border-box; }

html, body {
  margin: 0; padding: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--body);
  font-size: 17px;
  font-feature-settings: "liga", "kern", "onum";
  font-optical-sizing: auto;
  background-image:
    radial-gradient(circle at 12% 18%, rgba(200,85,61,0.04), transparent 38%),
    radial-gradient(circle at 88% 72%, rgba(59,95,78,0.05), transparent 42%),
    repeating-linear-gradient(45deg, rgba(31,27,22,0.014) 0 1px, transparent 1px 6px);
  min-height: 100vh;
}

a { color: inherit; text-decoration: none; border-bottom: 1px solid var(--rule); transition: border-color 0.2s; }
a:hover { border-bottom-color: var(--accent); }

.masthead {
  border-top: 4px double var(--ink);
  border-bottom: 1px solid var(--ink);
  padding: 22px 60px 18px;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: end;
  gap: 28px;
}
.masthead .kicker {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--ink-soft);
}
.masthead .issue-line { text-align: center; font-family: var(--mono); font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--ink-soft); }
.masthead .date { text-align: right; font-family: var(--mono); font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--ink-soft); }

.banner {
  position: relative;
  padding: 60px 60px 48px;
  border-bottom: 4px double var(--ink);
  overflow: hidden;
}
.banner::before {
  content: "";
  position: absolute; inset: 0;
  background-image:
    repeating-linear-gradient(90deg, transparent 0 38px, rgba(31,27,22,0.04) 38px 39px),
    repeating-linear-gradient(0deg, transparent 0 38px, rgba(31,27,22,0.04) 38px 39px);
  pointer-events: none;
  opacity: 0.5;
}
.banner-inner { position: relative; display: grid; grid-template-columns: 1fr auto; gap: 40px; align-items: end; }
.banner h1 {
  font-family: var(--serif);
  font-variation-settings: "opsz" 144, "wght" 480, "SOFT" 50, "WONK" 1;
  font-size: clamp(56px, 9vw, 132px);
  line-height: 0.86;
  margin: 0;
  letter-spacing: -0.02em;
}
.banner h1 .accent { color: var(--accent); font-variation-settings: "opsz" 144, "wght" 360, "SOFT" 100, "WONK" 1; font-style: italic; }
.banner h1 em { font-style: italic; font-variation-settings: "opsz" 144, "wght" 360, "SOFT" 100; }
.banner .deck {
  max-width: 540px;
  font-family: var(--body);
  font-size: 19px;
  line-height: 1.55;
  color: var(--ink-soft);
  font-style: italic;
}
.banner .meta-col { text-align: right; font-family: var(--mono); font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--ink-soft); line-height: 1.8; }
.banner .meta-col strong { color: var(--ink); display: block; font-size: 14px; letter-spacing: 0.08em; }

main { padding: 56px 60px 80px; max-width: 1480px; margin: 0 auto; }

.section-rule {
  display: flex; align-items: baseline; gap: 18px; margin: 48px 0 24px;
}
.section-rule .num {
  font-family: var(--serif); font-variation-settings: "opsz" 96, "wght" 400, "WONK" 1;
  font-style: italic; font-size: 64px; line-height: 1; color: var(--accent);
}
.section-rule .label {
  font-family: var(--mono); font-size: 12px; letter-spacing: 0.22em;
  text-transform: uppercase; color: var(--ink-soft); flex: 1;
}
.section-rule::after { content: ""; flex: 0 0 240px; height: 1px; background: var(--ink); margin-bottom: 8px; }

.kpi-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
  border-top: 1px solid var(--ink);
  border-bottom: 1px solid var(--ink);
}
.kpi {
  padding: 22px 24px 26px;
  border-right: 1px solid var(--rule);
  position: relative;
}
.kpi:last-child { border-right: none; }
.kpi .num { font-family: var(--serif); font-variation-settings: "opsz" 96, "wght" 460, "WONK" 1; font-size: 64px; line-height: 0.96; color: var(--ink); letter-spacing: -0.02em; }
.kpi .num em { font-style: italic; color: var(--accent); }
.kpi .label { font-family: var(--mono); font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--ink-soft); margin-top: 8px; display: block; }
.kpi .delta { font-family: var(--mono); font-size: 12px; color: var(--accent-deep); margin-top: 4px; }

.issue-shelf {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
  gap: 32px 28px;
  margin-top: 12px;
}
.issue-card {
  border-top: 1px solid var(--ink);
  padding: 18px 4px 18px;
  position: relative;
  display: block;
}
.issue-card .issue-num {
  font-family: var(--mono); font-size: 11px; letter-spacing: 0.18em;
  text-transform: uppercase; color: var(--accent); display: block;
}
.issue-card h3 {
  font-family: var(--serif); font-variation-settings: "opsz" 72, "wght" 540, "SOFT" 30;
  font-size: 26px; line-height: 1.12; margin: 6px 0 8px; letter-spacing: -0.012em;
}
.issue-card h3 em { font-style: italic; color: var(--accent); font-variation-settings: "opsz" 72, "wght" 380, "SOFT" 100, "WONK" 1; }
.issue-card .deck { font-family: var(--body); font-size: 14px; color: var(--ink-soft); line-height: 1.45; font-style: italic; margin-bottom: 12px; }
.issue-card .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; padding-top: 12px; border-top: 1px dotted var(--rule); font-family: var(--mono); font-size: 11px; letter-spacing: 0.04em; color: var(--ink-soft); }
.issue-card .stats strong { display: block; font-family: var(--serif); font-variation-settings: "opsz" 48, "wght" 540; font-size: 22px; color: var(--ink); }
.issue-card .severity { display: inline-block; padding: 1px 7px; border: 1px solid currentColor; margin-right: 4px; border-radius: 2px; font-family: var(--mono); font-size: 10px; }
.issue-card .severity.critical { color: var(--critical); }
.issue-card .severity.warning { color: var(--warn); }
.issue-card .severity.info { color: var(--muted); }

.cover {
  position: relative;
  padding: 60px 60px 70px;
  border-bottom: 4px double var(--ink);
  background: linear-gradient(180deg, var(--paper) 70%, var(--paper-deep));
}
.cover .issue-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 24px; font-family: var(--mono); font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--ink-soft); margin-bottom: 30px; }
.cover .issue-meta strong { color: var(--ink); display: block; font-size: 13px; letter-spacing: 0.12em; margin-top: 2px; }
.cover h1 {
  font-family: var(--serif); font-variation-settings: "opsz" 144, "wght" 420, "WONK" 1;
  font-size: clamp(40px, 6.5vw, 92px); line-height: 0.92; margin: 14px 0 18px; letter-spacing: -0.018em;
}
.cover h1 em { color: var(--accent); font-style: italic; font-variation-settings: "opsz" 144, "wght" 320, "SOFT" 100; }
.cover .deck { font-family: var(--body); font-style: italic; font-size: 21px; line-height: 1.45; color: var(--ink-soft); max-width: 760px; }

.article {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 60px;
  padding: 64px 60px 56px;
  border-bottom: 1px solid var(--ink);
  position: relative;
}
.article .column {
  font-family: var(--body);
  font-size: 18px;
  line-height: 1.62;
  max-width: 720px;
}
.article .column p { margin: 0 0 1.1em; hyphens: auto; }
.article .column p::first-letter {
  font-family: var(--serif);
  font-variation-settings: "opsz" 144, "wght" 520, "WONK" 1;
  font-size: 64px; line-height: 0.88; float: left; padding-right: 10px; padding-top: 4px; color: var(--accent);
}
.article h2, .article h3 {
  font-family: var(--serif); font-variation-settings: "opsz" 96, "wght" 520, "WONK" 0;
  margin: 1.6em 0 0.5em; letter-spacing: -0.012em;
}
.article h2 { font-size: 34px; border-bottom: 1px solid var(--ink); padding-bottom: 6px; line-height: 1.05; }
.article h2 em { font-style: italic; color: var(--accent); }
.article h3 { font-size: 22px; color: var(--ink-soft); border-bottom: none; }
.article .md-quote {
  border-left: 3px solid var(--accent);
  padding: 8px 18px; margin: 18px 0;
  font-family: var(--serif); font-style: italic; font-variation-settings: "opsz" 24, "wght" 420;
  font-size: 21px; line-height: 1.45; color: var(--ink-soft);
}
.article .md-list { padding-left: 1.3em; }
.article .md-list li { margin-bottom: 4px; }
.article .md-table { border-collapse: collapse; margin: 14px 0; font-size: 14px; width: 100%; font-family: var(--mono); }
.article .md-table th, .article .md-table td { border-bottom: 1px solid var(--rule); text-align: left; padding: 6px 10px; }
.article .md-table th { border-bottom: 1px solid var(--ink); color: var(--ink); font-weight: 500; text-transform: uppercase; font-size: 11px; letter-spacing: 0.08em; }
.article .md-code { background: var(--paper-deep); padding: 14px 18px; border-left: 3px solid var(--ink); overflow-x: auto; font-size: 13px; line-height: 1.5; }
.article code { background: var(--paper-deep); padding: 1px 5px; border-radius: 2px; font-family: var(--mono); font-size: 0.86em; }
.article .mn { font-family: var(--mono); }

.marginalia {
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: 0.02em;
  border-left: 1px solid var(--rule);
  padding-left: 22px;
  position: sticky;
  top: 24px;
}
.marginalia h4 {
  font-family: var(--mono); font-size: 11px; letter-spacing: 0.22em;
  text-transform: uppercase; color: var(--ink-soft); margin: 18px 0 8px;
  border-top: 1px solid var(--rule); padding-top: 16px;
}
.marginalia h4:first-child { border-top: none; padding-top: 0; }
.marginalia .mn-list { list-style: none; padding: 0; margin: 0; }
.marginalia .mn-list li { display: flex; gap: 10px; padding: 5px 0; border-bottom: 1px dotted var(--rule); }
.marginalia .mn-list .ref {
  flex: 0 0 22px; height: 22px; border: 1px solid var(--ink); border-radius: 50%;
  text-align: center; line-height: 20px; font-family: var(--serif); font-variation-settings: "opsz" 24, "wght" 600;
  font-size: 13px; color: var(--accent);
}
.marginalia .mn-list .body { color: var(--ink-soft); line-height: 1.42; }

.marginalia .anomaly-circle {
  display: inline-block; width: 22px; height: 22px; border: 1px solid var(--ink); border-radius: 50%;
  text-align: center; line-height: 20px; font-family: var(--serif);
  font-variation-settings: "opsz" 24, "wght" 600; font-size: 12px; color: var(--accent);
  position: relative; cursor: help;
}
.marginalia .anomaly-circle:hover { background: var(--accent); color: var(--paper); border-color: var(--accent); }
.marginalia .anomaly-circle[data-tooltip]:hover::after {
  content: attr(data-tooltip);
  position: absolute; left: 28px; top: -4px;
  background: var(--ink); color: var(--paper);
  padding: 6px 10px; border-radius: 4px; white-space: pre-wrap; max-width: 320px;
  z-index: 10; font-family: var(--mono); font-size: 11px; text-align: left; line-height: 1.4;
}

.endgrid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 48px; align-items: stretch; }
.endgrid + .endgrid { margin-top: 28px; }

.endtable { border-top: 1px solid var(--ink); border-bottom: 1px solid var(--ink); padding: 16px 0; font-family: var(--mono); }
.endtable table { width: 100%; border-collapse: collapse; }
.endtable th, .endtable td { padding: 7px 0; border-bottom: 1px solid var(--rule); font-size: 13px; }
.endtable th { text-align: left; font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--ink-soft); }
.endtable td.right, .endtable th.right { text-align: right; }
.endtable .bar { display: inline-block; height: 8px; background: var(--accent); vertical-align: middle; margin-right: 8px; }

.sparkblock { border: 1px solid var(--ink); background: var(--paper-deep); padding: 18px 20px; }
.sparkblock h4 { margin: 0 0 12px; font-family: var(--mono); font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--ink-soft); }
.sparkblock svg { display: block; width: 100%; height: auto; }
.sparkblock .legend { display: flex; gap: 16px; margin-top: 10px; font-family: var(--mono); font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--ink-soft); }
.sparkblock .legend span::before { content: "■"; margin-right: 5px; color: var(--accent); }

.playthrough-spine {
  border-top: 1px solid var(--ink); border-bottom: 1px solid var(--ink);
  padding: 28px 0; position: relative; margin-top: 24px;
  overflow-x: auto;
}
.playthrough-spine .axis { position: relative; min-width: 900px; height: 220px; }
.spine-line { position: absolute; left: 0; right: 0; top: 50%; border-top: 1px dashed var(--ink); }
.spine-week {
  position: absolute; top: 50%; transform: translate(-50%, -50%);
  width: 86px; text-align: center;
}
.spine-week .dot { display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: var(--ink); }
.spine-week .dot.alert { background: var(--accent); }
.spine-week .dot.normal { background: var(--forest); }
.spine-week .num { display: block; font-family: var(--serif); font-variation-settings: "opsz" 48, "wght" 540, "WONK" 1; font-style: italic; font-size: 22px; color: var(--accent); margin-bottom: 4px; }
.spine-week .actions { display: block; font-family: var(--mono); font-size: 10px; letter-spacing: 0.04em; color: var(--ink-soft); line-height: 1.3; max-height: 2.6em; overflow: hidden; }

.footnote-rail {
  margin-top: 28px; padding-top: 18px; border-top: 1px dotted var(--rule);
  display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px;
}
.footnote { font-family: var(--mono); font-size: 11px; line-height: 1.45; color: var(--ink-soft); border-left: 2px solid var(--accent); padding: 4px 0 4px 12px; }
.footnote strong { font-family: var(--serif); font-style: italic; color: var(--ink); display: block; font-size: 14px; font-weight: 400; margin-bottom: 4px; }

.colophon { padding: 36px 60px 60px; font-family: var(--mono); font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); border-top: 4px double var(--ink); }
.colophon .row { display: flex; justify-content: space-between; gap: 24px; }

/* Sparkline draw-on-load */
.sparkline-path {
  stroke-dasharray: 600;
  stroke-dashoffset: 600;
  animation: draw 1.2s ease-out forwards;
}
.sparkline-path.delay-1 { animation-delay: 0.15s; }
.sparkline-path.delay-2 { animation-delay: 0.3s; }
.sparkline-path.delay-3 { animation-delay: 0.45s; }
.sparkline-path.delay-4 { animation-delay: 0.6s; }
@keyframes draw { to { stroke-dashoffset: 0; } }

.fade-in { opacity: 0; animation: fadeIn 0.7s ease-out forwards; animation-delay: 0.2s; }
.fade-in.d1 { animation-delay: 0.4s; }
.fade-in.d2 { animation-delay: 0.6s; }
.fade-in.d3 { animation-delay: 0.8s; }
@keyframes fadeIn { to { opacity: 1; } }

.byline-rule { display: flex; align-items: center; gap: 14px; font-family: var(--mono); font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--ink-soft); margin: 18px 0; }
.byline-rule::before, .byline-rule::after { content: ""; flex: 1; border-top: 1px solid var(--rule); }

.tab-rail { display: flex; gap: 0; border-top: 1px solid var(--ink); border-bottom: 1px solid var(--ink); margin: 32px 0 24px; }
.tab-rail a { padding: 10px 18px; border-right: 1px solid var(--rule); border-bottom: 1px solid transparent; font-family: var(--mono); font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink-soft); }
.tab-rail a:hover { background: var(--paper-deep); border-bottom-color: var(--ink); }
.tab-rail a[aria-current="page"] { background: var(--ink); color: var(--paper); border-bottom-color: var(--ink); }

.error-banner { padding: 14px 18px; background: var(--critical); color: var(--paper); margin: 12px 0; font-family: var(--mono); font-size: 12px; }
.warn-banner { padding: 14px 18px; background: var(--warn); color: var(--paper); margin: 12px 0; font-family: var(--mono); font-size: 12px; }
.gate-pass { padding: 12px 18px; border: 1px solid var(--forest); color: var(--forest); font-family: var(--mono); font-size: 12px; margin: 12px 0; }
.gate-fail { padding: 12px 18px; border: 1px solid var(--critical); color: var(--critical); font-family: var(--mono); font-size: 12px; margin: 12px 0; }

@media (max-width: 960px) {
  .masthead, .banner, .article, .colophon, .cover { padding-left: 24px; padding-right: 24px; }
  .article { grid-template-columns: 1fr; }
  .kpi-strip { grid-template-columns: repeat(2, 1fr); }
  .endgrid { grid-template-columns: 1fr; }
}

/* ====================================================================== */
/* Decision-graph page                                                    */
/* ====================================================================== */

.graph-shell {
  padding: 0 60px 48px;
  max-width: 1640px;
  margin: 0 auto;
}
.graph-stage {
  border-top: 4px double var(--ink);
  border-bottom: 4px double var(--ink);
  background:
    repeating-linear-gradient(0deg, transparent 0 23px, rgba(31,27,22,0.04) 23px 24px),
    var(--paper-deep);
  position: relative;
  overflow-x: auto;
}
.graph-stage svg { display: block; width: 100%; min-width: 1100px; height: auto; }

.graph-stage .lane-band {
  fill: rgba(217, 210, 197, 0.32);
}
.graph-stage .lane-label {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  fill: var(--ink-soft);
}
.graph-stage .week-tick {
  stroke: var(--rule);
  stroke-width: 1;
}
.graph-stage .week-tick-text {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  fill: var(--ink-soft);
}
.graph-stage .event-node {
  fill: var(--paper);
  stroke: var(--muted);
  stroke-width: 1;
  cursor: pointer;
  transition: r 0.15s ease, stroke 0.15s ease, fill 0.15s ease;
}
.graph-stage .event-node.fixed { stroke: var(--ink); }
.graph-stage .event-node.conditional { stroke: var(--forest); stroke-dasharray: 2 2; }
.graph-stage .event-node.random { stroke: var(--muted); stroke-dasharray: 1 3; }
.graph-stage .event-node.triggered { fill: var(--ink); stroke: var(--ink); }
.graph-stage .event-node:hover { r: 8; fill: var(--accent); stroke: var(--accent); }
.graph-stage .event-node.is-current { fill: var(--accent); stroke: var(--accent); }

.graph-stage .path-edge {
  stroke: var(--accent);
  stroke-width: 1.4;
  fill: none;
  opacity: 0.55;
}
.graph-stage .path-edge.is-current { stroke-width: 2.4; opacity: 1; }

.graph-stage .agent-path {
  fill: none;
  stroke: var(--accent);
  stroke-width: 2.6;
  stroke-linecap: round;
  stroke-linejoin: round;
  filter: drop-shadow(0 0 8px rgba(200,85,61,0.45));
  stroke-dasharray: 3000;
  stroke-dashoffset: 3000;
  animation: drawPath 1.6s ease-out forwards;
}
@keyframes drawPath { to { stroke-dashoffset: 0; } }

.graph-stage .choice-wedge {
  fill: var(--paper);
  opacity: 0.9;
  transition: opacity 0.2s ease;
}
.graph-stage .event-node:hover ~ .choice-wedge,
.graph-stage .event-node.is-current ~ .choice-wedge { opacity: 1; }
.graph-stage .choice-index {
  font-family: var(--mono);
  font-size: 9px;
  fill: var(--ink);
  pointer-events: none;
  font-weight: 600;
}

.graph-stage .lane-end-marker {
  fill: var(--forest);
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.12em;
}

.graph-tooltip {
  position: fixed;
  z-index: 200;
  max-width: 360px;
  padding: 12px 14px;
  background: var(--ink);
  color: var(--paper);
  font-family: var(--mono);
  font-size: 11px;
  line-height: 1.5;
  border-left: 3px solid var(--accent);
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s ease;
  box-shadow: 0 14px 28px rgba(31,27,22,0.18);
}
.graph-tooltip.is-visible { opacity: 1; }
.graph-tooltip .tt-event-id { color: var(--accent); font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase; display: block; margin-bottom: 4px; }
.graph-tooltip .tt-event-title { font-family: var(--serif); font-variation-settings: "opsz" 24, "wght" 480; font-style: italic; font-size: 16px; line-height: 1.3; display: block; margin-bottom: 6px; color: var(--paper); }
.graph-tooltip .tt-choice { display: block; margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(244,239,230,0.18); }
.graph-tooltip .tt-choice .pick { color: var(--accent); font-weight: 600; }
.graph-tooltip .tt-choice .text { color: var(--paper); display: block; margin-top: 2px; font-style: italic; }

.timeline-rail {
  border-top: 1px solid var(--ink);
  border-bottom: 1px solid var(--ink);
  padding: 22px 24px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 24px;
  align-items: center;
  background: var(--paper-deep);
}
.timeline-strip {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 56px;
  gap: 4px;
  overflow-x: auto;
}
.timeline-cell {
  border: 1px solid var(--rule);
  background: var(--paper);
  padding: 6px 4px;
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.02em;
  text-align: center;
  cursor: pointer;
  position: relative;
  min-height: 56px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.timeline-cell:hover { background: var(--paper-deep); border-color: var(--ink); }
.timeline-cell.is-current { background: var(--accent); color: var(--paper); border-color: var(--accent-deep); }
.timeline-cell.is-triggered { border-color: var(--accent); }
.timeline-cell .w { display: block; font-family: var(--serif); font-variation-settings: "opsz" 24, "wght" 540; font-style: italic; font-size: 18px; color: var(--accent); line-height: 1; }
.timeline-cell.is-current .w { color: var(--paper); }
.timeline-cell .dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--muted); margin-top: 4px; }
.timeline-cell.is-triggered .dot { background: var(--accent); }

.timeline-controls { display: flex; flex-direction: column; gap: 8px; align-items: stretch; min-width: 220px; font-family: var(--mono); font-size: 11px; letter-spacing: 0.08em; }
.timeline-controls .row { display: flex; gap: 10px; align-items: center; }
.timeline-controls button {
  font-family: var(--mono); font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase;
  background: var(--paper); color: var(--ink); border: 1px solid var(--ink); padding: 6px 12px; cursor: pointer;
}
.timeline-controls button:hover { background: var(--ink); color: var(--paper); }
.timeline-controls input[type="range"] { flex: 1; accent-color: var(--accent); }
.timeline-controls .legend { display: flex; gap: 14px; flex-wrap: wrap; color: var(--ink-soft); }
.timeline-controls .legend span::before { content: "■"; color: var(--accent); margin-right: 5px; }
.timeline-controls .legend .dot-line::before { color: var(--muted); }

.graph-side-panel {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 32px;
  margin-top: 28px;
}
.graph-side-panel .panel-card {
  border: 1px solid var(--ink);
  background: var(--paper);
  padding: 18px 22px;
  font-family: var(--mono);
  font-size: 12px;
  line-height: 1.55;
  color: var(--ink-soft);
}
.graph-side-panel .panel-card h4 {
  font-family: var(--mono); font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase;
  color: var(--ink-soft); margin: 0 0 10px;
}
.graph-side-panel .panel-card .pick-label { color: var(--accent); font-weight: 600; }
.graph-side-panel .panel-card .pick-text { font-family: var(--serif); font-variation-settings: "opsz" 24, "wght" 420; font-style: italic; font-size: 18px; line-height: 1.4; color: var(--ink); display: block; margin: 6px 0 10px; }
.graph-side-panel .panel-card .effects { display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px 12px; }
.graph-side-panel .panel-card .effects span { font-family: var(--mono); font-size: 11px; }
.graph-side-panel .panel-card .effects .pos { color: var(--forest); }
.graph-side-panel .panel-card .effects .neg { color: var(--accent-deep); }

.legend-row { display: flex; gap: 18px; flex-wrap: wrap; align-items: center; font-family: var(--mono); font-size: 11px; letter-spacing: 0.08em; color: var(--ink-soft); margin: 18px 0; }
.legend-row .swatch { display: inline-block; width: 14px; height: 14px; border-radius: 50%; vertical-align: middle; margin-right: 6px; border: 1px solid var(--ink); }
.legend-row .swatch.fixed { background: var(--paper); border-color: var(--ink); }
.legend-row .swatch.conditional { background: var(--paper); border-color: var(--forest); border-style: dashed; }
.legend-row .swatch.random { background: var(--paper); border-color: var(--muted); border-style: dotted; }
.legend-row .swatch.path { background: var(--accent); border-color: var(--accent); }

.graph-footnote {
  font-family: var(--serif);
  font-variation-settings: "opsz" 24, "wght" 380, "SOFT" 60;
  font-style: italic;
  font-size: 14px;
  color: var(--ink-soft);
  border-left: 3px solid var(--accent);
  padding: 6px 0 6px 16px;
  margin: 24px 0 0;
  max-width: 720px;
}

@media (max-width: 960px) {
  .graph-shell { padding-left: 18px; padding-right: 18px; }
  .graph-side-panel { grid-template-columns: 1fr; }
  .timeline-rail { grid-template-columns: 1fr; }
}
"""


def _svg_sparkline(
    series: list[tuple[float, float]],  # list of (week, value)
    *,
    width: int = 720,
    height: int = 140,
    label: str = "",
    color: str = "var(--accent)",
    delay: int = 0,
) -> str:
    if not series:
        return ""
    xs = [s[0] for s in series]
    ys = [s[1] for s in series]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    if x_max == x_min:
        x_max = x_min + 1
    if y_max == y_min:
        y_max = y_min + 1
    pts = []
    for x, y in series:
        px = (x - x_min) / (x_max - x_min) * (width - 20) + 10
        py = (1 - (y - y_min) / (y_max - y_min)) * (height - 30) + 10
        pts.append((px, py))
    path = " ".join(
        f"{'M' if i == 0 else 'L'} {px:.1f} {py:.1f}" for i, (px, py) in enumerate(pts)
    )
    last_y = pts[-1][1]
    last_x = pts[-1][0]
    return (
        f"<svg viewBox='0 0 {width} {height}' role='img' aria-label='{html.escape(label)}'>"
        f"<path class='sparkline-path delay-{min(delay,4)}' d='{path}' "
        f"stroke='{color}' stroke-width='2' fill='none' />"
        f"<circle cx='{last_x:.1f}' cy='{last_y:.1f}' r='3' fill='{color}' />"
        f"</svg>"
    )


def _spark_block_for_metric(
    issue: Issue, metric: str, *, color: str, delay: int
) -> str:
    series = sorted(
        (p.week, p.mean) for p in issue.weekly_series if p.metric == metric
    )
    if not series:
        return ""
    svg = _svg_sparkline(
        series, label=f"{metric} by week", color=color, delay=delay
    )
    return (
        "<div class='sparkblock'>"
        f"<h4>{html.escape(metric)}</h4>"
        f"{svg}"
        "</div>"
    )


def _top_findings_table(findings: list[dict], *, limit: int = 6) -> str:
    if not findings:
        return "<div class='footnote'>No findings recorded.</div>"
    rows = findings[:limit]
    body = "".join(
        "<tr>"
        f"<td><span class='severity {html.escape(str(f.get('severity','')))}'>{html.escape(str(f.get('severity','')))}</span></td>"
        f"<td>{html.escape(str(f.get('description',''))[:160])}</td>"
        f"<td class='right'>{html.escape(str(f.get('value','')))}</td>"
        "</tr>"
        for f in rows
    )
    return (
        "<div class='endtable'>"
        "<table>"
        "<thead><tr><th>sev</th><th>finding</th><th class='right'>value</th></tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
        "</div>"
    )


def _anomaly_marginalia(issue: Issue) -> str:
    if not issue.anomalies:
        return ""
    items: list[str] = []
    for idx, anomaly in enumerate(issue.anomalies[:12], start=1):
        kind = str(anomaly.get("kind", ""))
        sev = str(anomaly.get("severity", "info"))
        run = str(anomaly.get("run_id", "-"))
        week = str(anomaly.get("week", "-"))
        msg = str(anomaly.get("message", ""))
        tooltip = f"{kind} · run {run} · week {week}\n{msg}"
        items.append(
            "<li>"
            f"<span class='anomaly-circle' data-tooltip=\"{html.escape(tooltip, quote=True)}\">{idx}</span>"
            f"<span class='body'>#{idx} · {html.escape(kind)}<br>run {run}, w{week}, {html.escape(sev)}</span>"
            "</li>"
        )
    if not items:
        return ""
    body = "\n".join(items)
    return (
        "<h4>Anomaly marginalia</h4>"
        f"<ul class='mn-list'>{body}</ul>"
    )


def _playthrough_spine(issue: Issue) -> str:
    weeks = []
    for idx, run in enumerate(issue.playthrough):
        rows = run.get("weekly_log", []) or []
        for w in rows:
            weeks.append(w)
    if not weeks:
        return ""
    max_week = max((w.get("week", 0) for w in weeks), default=0)
    if max_week <= 0:
        return ""
    nodes: list[str] = []
    for w in sorted(weeks, key=lambda w: w.get("week", 0)):
        week_no = int(w.get("week", 0))
        actions = w.get("selected_action_ids") or w.get("actions") or []
        action_str = ", ".join(str(a) for a in actions[:2])[:60]
        anomalies = len(w.get("anomalies", []) or [])
        dot_cls = "alert" if anomalies else "normal"
        left = week_no / max(max_week, 1) * 100
        nodes.append(
            f"<div class='spine-week' style='left:{left:.1f}%'>"
            f"<span class='num'>{week_no}</span>"
            f"<span class='dot {dot_cls}'></span>"
            f"<span class='actions'>{html.escape(action_str)}</span>"
            "</div>"
        )
    return (
        "<div class='playthrough-spine'>"
        "<h3 style='font-family:var(--serif);font-style:italic;margin:0 0 18px;"
        "font-variation-settings:\"opsz\" 96, \"wght\" 420, \"SOFT\" 100;'>"
        f"The {len(weeks)}-week spine</h3>"
        f"<div class='axis'><div class='spine-line'></div>{''.join(nodes)}</div>"
        "</div>"
    )


def _fmt_run_kpis(issues: list[Issue]) -> tuple[int, int, int, int]:
    total_runs = 0
    total_anomalies = 0
    total_critical = 0
    total_findings = 0
    for issue in issues:
        total_runs += issue.total_runs
        total_anomalies += len(issue.anomalies)
        total_findings += len(issue.value_findings) + len(issue.route_findings)
        for a in issue.anomalies:
            if str(a.get("severity", "")) == "critical":
                total_critical += 1
    return total_runs, total_anomalies, total_critical, total_findings


# ---------------------------------------------------------------------------
# Decision-graph view
# ---------------------------------------------------------------------------


@dataclass
class _GraphLayout:
    """Result of computing where every event sits in 2D space."""

    width: int
    height: int
    max_week: int
    positions: dict[str, tuple[float, float]]  # event_id -> (x, y)
    lane_y: dict[str, float]
    lane_order: list[str]  # ordered list of lane names actually present
    events: list[dict]
    event_index: dict[str, dict]


def _trigger_week(trigger: Any) -> float | None:
    """Extract a canonical 'when does this fire' week from any trigger shape.

    Tolerates the legacy ``{"week": N}`` shape plus several likely renames.
    Returns ``None`` when the trigger has no numeric week hint.
    """
    if not isinstance(trigger, dict):
        return None
    for key in ("week", "min_week", "start_week", "first_week", "at_week", "fire_week"):
        value = trigger.get(key)
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
    # Some games use a list of weeks: ``{"weeks": [1, 3, 5]}`` — pick the first.
    weeks_list = trigger.get("weeks")
    if isinstance(weeks_list, list) and weeks_list:
        first = weeks_list[0]
        if isinstance(first, (int, float)) and first >= 0:
            return float(first)
    return None


def _lane_for_event(ev: dict) -> str:
    """Resolve an event's lane name from any reasonable shape.

    Falls back to ``"uncategorised"`` so unknown types still get a lane
    rather than being silently dropped or merged into another lane.
    """
    ev_type = ev.get("event_type") or ev.get("type") or ev.get("kind")
    if not isinstance(ev_type, str) or not ev_type.strip():
        return "uncategorised"
    return ev_type.strip().lower()


_LANE_PRIORITY = {
    "fixed": 0,
    "conditional": 1,
    "random": 2,
    "uncategorised": 99,
}


def _compute_graph_layout(
    events: list[dict], *, max_week: int = 20, width: int = 1280, height: int | None = None
) -> _GraphLayout:
    """Place every event on a 2D canvas.

    Lanes are *derived* from the actual ``event_type`` values present in
    ``events`` — adding a new event type creates a new lane automatically.
    Lane y positions are computed from the number of lanes, so the layout
    rebalances whether the game has 1 lane or 10.

    X = week (extracted via :func:`_trigger_week`, fallback to source_order).
    Y = lane anchor + jitter so events in the same lane don't stack exactly.
    """
    # Bucket events by lane name.
    by_lane: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        by_lane[_lane_for_event(ev)].append(ev)

    # Dominant lanes should appear first as the event tree evolves; ties keep
    # familiar lanes in semantic order and unknown lanes deterministic.
    lane_order = sorted(
        by_lane.keys(),
        key=lambda name: (-len(by_lane[name]), _LANE_PRIORITY.get(name, 50), name),
    )

    # Auto-size the canvas vertically to fit the lanes comfortably.
    pad_top = 80
    pad_bottom = 60
    lane_band = 130
    if height is None:
        height = max(pad_top + pad_bottom + lane_band * len(lane_order), 320)
    pad_left = 130
    pad_right = 60
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    # Compute lane y anchors evenly spaced.
    lane_y: dict[str, float] = {}
    n_lanes = max(len(lane_order), 1)
    for idx, lane_name in enumerate(lane_order):
        if n_lanes == 1:
            lane_y[lane_name] = pad_top + plot_h / 2
        else:
            lane_y[lane_name] = pad_top + (idx + 0.5) * (plot_h / n_lanes)

    positions: dict[str, tuple[float, float]] = {}
    event_index: dict[str, dict] = {}
    for ev in events:
        ev_id = ev.get("id")
        if not ev_id:
            continue
        event_index[ev_id] = ev

    for lane_name, lane_events in by_lane.items():
        anchor_y = lane_y[lane_name]
        # Within a lane, sort by trigger week (or source_order) so the X axis
        # reads chronologically when there is one.
        lane_events_sorted = sorted(
            lane_events,
            key=lambda e: (
                _trigger_week(e.get("trigger") or {}) if _trigger_week(e.get("trigger") or {}) is not None
                else float(e.get("source_order", 0) or 0) * 100
            ),
        )
        for idx, ev in enumerate(lane_events_sorted):
            ev_id = ev.get("id")
            if not ev_id:
                continue
            week = _trigger_week(ev.get("trigger") or {})
            if week is not None:
                x = pad_left + (week / max_week) * plot_w
            else:
                # No week hint — distribute along the X axis by source_order
                # (or by enumeration index if source_order is missing).
                order = ev.get("source_order")
                if not isinstance(order, (int, float)):
                    order = idx
                x = pad_left + (float(order) / max(len(lane_events), 1)) * plot_w
            # Subtle vertical jitter so dots in the same week don't overlap.
            order = ev.get("source_order", 0) or 0
            offset = ((order % 7) - 3) * 8  # -24..+24 px
            positions[ev_id] = (x, anchor_y + offset)

    return _GraphLayout(
        width=width,
        height=height,
        max_week=max_week,
        positions=positions,
        lane_y=lane_y,
        lane_order=lane_order,
        events=events,
        event_index=event_index,
    )


def _wedge_path(
    cx: float, cy: float, r: float, idx: int, total: int
) -> str:
    """Build the SVG path for one wedge of a pie chart."""
    if total <= 0:
        return ""
    start_angle = -90.0 + (360.0 / total) * idx
    end_angle = -90.0 + (360.0 / total) * (idx + 1)
    large_arc = 1 if (end_angle - start_angle) > 180 else 0
    sx = cx + r * math.cos(math.radians(start_angle))
    sy = cy + r * math.sin(math.radians(start_angle))
    ex = cx + r * math.cos(math.radians(end_angle))
    ey = cy + r * math.sin(math.radians(end_angle))
    return (
        f"M {cx:.2f} {cy:.2f} L {sx:.2f} {sy:.2f} "
        f"A {r:.2f} {r:.2f} 0 {large_arc} 1 {ex:.2f} {ey:.2f} Z"
    )


def _choice_index_from_id(choice_id: str, num_choices: int) -> int:
    """Recover the 0-indexed choice index from any reasonable choice_id.

    Tolerates multiple on-the-wire shapes:

    * ``first_lecture.choice_01_ask_question`` — current convention
    * ``first_lecture.choice_01``
    * ``first_lecture/c1``
    * ``first_lecture:1``
    * ``first_lecture_1``

    Falls back to ``-1`` (no wedge rendered) when no pattern matches.
    """
    if not choice_id or num_choices <= 0:
        return -1
    patterns = [
        r"\.choice_(\d+)_",   # event.choice_01_text
        r"\.choice_(\d+)$",   # event.choice_01
        r"/c(\d+)$",          # event/c1
        r"/choice(\d+)$",     # event/choice1
        r":choice_?(\d+)$",   # event:choice1
        r":(\d+)$",           # event:1
        r"_(\d+)$",           # event_1
    ]
    for pat in patterns:
        match = re.search(pat, choice_id)
        if match:
            idx = int(match.group(1)) - 1  # 1-indexed → 0-indexed
            if 0 <= idx < num_choices:
                return idx
    return -1


def _choice_index_from_record(week: dict, choices: list) -> int:
    """Resolve the choice index from a weekly_log entry, with three fallbacks:

    1. An explicit ``choice_index`` field on the week record (when the game
       has been upgraded to emit one directly).
    2. Parse the ``event_choice_id`` via :func:`_choice_index_from_id`.
    3. Look at a ``selected_choice_index`` / ``choice_index`` numeric field
       just in case the schema uses a different name.
    Returns ``-1`` if nothing usable is found.
    """
    explicit = week.get("choice_index")
    if isinstance(explicit, int) and 0 <= explicit < len(choices):
        return explicit
    explicit = week.get("selected_choice_index")
    if isinstance(explicit, int) and 0 <= explicit < len(choices):
        return explicit
    return _choice_index_from_id(
        str(week.get("event_choice_id") or ""), len(choices)
    )


def _safe_get_choice_text(choice: Any) -> str:
    """Return the human-readable text of a choice, accepting several shapes."""
    if not isinstance(choice, dict):
        return ""
    for key in ("text", "label", "name", "description", "title"):
        value = choice.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _safe_get_choice_effects(choice: Any) -> dict[str, float]:
    """Return the effects dict of a choice, accepting ``success_effects`` /
    ``failure_effects`` / a single ``effects`` field."""
    if not isinstance(choice, dict):
        return {}
    for key in ("success_effects", "effects", "outcome_effects"):
        value = choice.get(key)
        if isinstance(value, dict):
            return {str(k): float(v) for k, v in value.items() if isinstance(v, (int, float))}
    return {}


def _decision_graph_payload(
    event_graph: dict, run: dict
) -> dict:
    """Compute the layout + path geometry + per-week metadata for the graph page.

    Tolerates many schema variations:

    * Missing / renamed ``trigger`` keys (``fire_week``, ``min_week``, …).
    * New ``event_type`` values that aren't ``fixed`` / ``conditional`` /
      ``random``.
    * Choice text + effects stored under different field names.
    * Weekly-log entries whose ``event_choice_id`` matches a different
      naming convention than the legacy ``event.choice_NN_text``.
    """
    max_week_raw = run.get("max_weeks") or run.get("weeks") or 20
    try:
        max_week = int(max_week_raw)
    except (TypeError, ValueError):
        max_week = 20
    # If the run blew past max_weeks (anomaly), widen the plot so the path fits.
    log = run.get("weekly_log") or []
    if log:
        observed_max_week = max(
            (int(w.get("week", 0) or 0) for w in log if isinstance(w, dict)),
            default=max_week,
        )
        max_week = max(max_week, observed_max_week)

    layout = _compute_graph_layout(
        event_graph.get("events") or [], max_week=max_week
    )
    triggered_events: list[dict] = []
    seen_event_ids: list[str] = []
    diagnostics: list[str] = []  # textual log of what we adapted to

    for week in log:
        if not isinstance(week, dict):
            diagnostics.append(f"Skipped non-dict weekly_log entry: {type(week).__name__}")
            continue
        ev_id = (
            week.get("triggered_event_id")
            or week.get("event_id")
            or week.get("event")
            or ""
        )
        if not ev_id:
            continue
        ev = layout.event_index.get(ev_id)
        if not ev:
            diagnostics.append(f"Triggered event {ev_id!r} not found in event_graph.json — skipped")
            continue
        seen_event_ids.append(ev_id)
        choices = ev.get("choices") or []
        choice_index = _choice_index_from_record(week, choices)
        if choice_index == -1 and week.get("event_choice_id"):
            diagnostics.append(
                f"Could not parse choice_index from event_choice_id={week.get('event_choice_id')!r} for {ev_id} (choices={len(choices)})"
            )
        choice_text = (
            _safe_get_choice_text(choices[choice_index]) if 0 <= choice_index < len(choices) else ""
        )
        choice_effects = (
            _safe_get_choice_effects(choices[choice_index]) if 0 <= choice_index < len(choices) else {}
        )
        try:
            week_no = int(week.get("week", 0) or 0)
        except (TypeError, ValueError):
            week_no = 0
            diagnostics.append(f"Bad 'week' value {week.get('week')!r} for {ev_id}")
        triggered_events.append(
            {
                "week": week_no,
                "event_id": ev_id,
                "title": str(ev.get("title") or ""),
                "body": str(ev.get("body") or ""),
                "event_type": _lane_for_event(ev),
                "choice_index": choice_index,
                "choice_id": str(week.get("event_choice_id") or ""),
                "choice_text": choice_text,
                "choice_effects": choice_effects,
                "selected_actions": [
                    str(a) for a in (
                        week.get("selected_action_ids")
                        or week.get("actions")
                        or []
                    )
                ],
                "after_state": dict(week.get("after_state") or week.get("state") or {}),
                "x": layout.positions.get(ev_id, (0, 0))[0],
                "y": layout.positions.get(ev_id, (0, 0))[1],
            }
        )

    return {
        "layout": layout,
        "run": run,
        "events": triggered_events,
        "ending_id": str(
            run.get("final_ending_id")
            or run.get("ending_id")
            or run.get("last_ending_id")
            or ""
        ),
        "final_state": run.get("final_state") or {},
        "policy": str(run.get("policy") or ""),
        "scenario": str(run.get("scenario") or ""),
        "seed": run.get("seed"),
        "seed_display": str(run.get("seed") if run.get("seed") is not None else "—"),
        "max_week": max_week,
        "all_event_ids": [
            ev.get("id") for ev in event_graph.get("events", []) if isinstance(ev, dict) and ev.get("id")
        ],
        "diagnostics": diagnostics,
        "lane_order": layout.lane_order,
    }


def _decision_graph_svg(payload: dict) -> str:
    """Render the SVG of the decision graph (events + path + wedges)."""
    layout: _GraphLayout = payload["layout"]
    triggered = payload["events"]
    triggered_by_id = {e["event_id"]: e for e in triggered}
    # Path data: ordered (x, y) through triggered events.
    path_points = " ".join(
        f"{e['x']:.2f},{e['y']:.2f}" for e in triggered
    )
    # Edges (curved lines between consecutive triggered events)
    edges: list[str] = []
    for prev, curr in zip(triggered, triggered[1:], strict=False):
        x1, y1 = prev["x"], prev["y"]
        x2, y2 = curr["x"], curr["y"]
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2 - 30
        edges.append(
            f'<path class="path-edge" d="M {x1:.1f} {y1:.1f} Q {mid_x:.1f} {mid_y:.1f} {x2:.1f} {y2:.1f}" />'
        )

    # Lane bands (height auto-scales to the number of lanes)
    lane_bands = []
    lane_labels = []
    lane_name_counts = {name: 0 for name in layout.lane_order}
    for ev in layout.events:
        lane_name = _lane_for_event(ev)
        lane_name_counts[lane_name] = lane_name_counts.get(lane_name, 0) + 1
    n_lanes = max(len(layout.lane_order), 1)
    band_height = (layout.height - 80 - 60) / n_lanes
    for lane_name in layout.lane_order:
        lane_y = layout.lane_y[lane_name]
        lane_bands.append(
            f'<rect class="lane-band" x="60" y="{lane_y - band_height / 2:.1f}" '
            f'width="{layout.width - 120:.1f}" height="{band_height:.1f}" />'
        )
        lane_labels.append(
            f'<text class="lane-label" x="20" y="{lane_y - band_height / 2 + 18:.1f}">{html.escape(lane_name.upper())}</text>'
        )
        lane_labels.append(
            f'<text class="lane-label" x="20" y="{lane_y - band_height / 2 + 32:.1f}" '
            f'style="font-size:9px;letter-spacing:0.1em">{lane_name_counts.get(lane_name, 0)} events</text>'
        )

    # Week tick marks (anchored to the bottom of the plot area).
    week_ticks = []
    week_axis_y = layout.height - 50
    week_label_y = layout.height - 26
    for w in range(0, payload["max_week"] + 1):
        x = 130 + (w / payload["max_week"]) * (layout.width - 130 - 60)
        week_ticks.append(
            f'<line class="week-tick" x1="{x:.1f}" y1="{week_axis_y}" x2="{x:.1f}" y2="{week_axis_y + 8}" />'
            f'<text class="week-tick-text" x="{x:.1f}" y="{week_label_y}" text-anchor="middle">W{w}</text>'
        )

    # All events (background)
    all_event_dots = []
    for ev in layout.events:
        ev_id = ev.get("id")
        if not ev_id or ev_id in triggered_by_id:
            continue
        pos = layout.positions.get(ev_id)
        if not pos:
            continue
        x, y = pos
        lane_name = _lane_for_event(ev)
        all_event_dots.append(
            f'<circle class="event-node {html.escape(lane_name)}" cx="{x:.1f}" cy="{y:.1f}" '
            f'r="3.2" data-event-id="{html.escape(ev_id)}">'
            f'<title>{html.escape(ev.get("title", ev_id))}</title>'
            f'</circle>'
        )

    # Triggered event nodes + choice wedges
    triggered_drawn = []
    for ev in triggered:
        ev_id = ev["event_id"]
        cx, cy = ev["x"], ev["y"]
        lane_name = _lane_for_event(layout.event_index.get(ev_id, {}))
        ev_index = layout.event_index.get(ev_id, {})
        choices = ev_index.get("choices") or []
        choice_index = ev["choice_index"]
        triggered_drawn.append(
            f'<g class="path-event-group" data-week="{ev["week"]}" data-event-id="{html.escape(ev_id)}">'
            f'<circle class="event-node triggered {html.escape(lane_name)}" cx="{cx:.1f}" cy="{cy:.1f}" '
            f'r="9" data-event-id="{html.escape(ev_id)}" data-week="{ev["week"]}" data-choice-index="{choice_index}">'
            f'<title>W{ev["week"]} · {html.escape(ev.get("title", ev_id))}</title>'
            f'</circle>'
        )
        if 0 <= choice_index < len(choices) and len(choices) > 1:
            wedge = _wedge_path(cx, cy, 9, choice_index, len(choices))
            triggered_drawn.append(
                f'<path class="choice-wedge" d="{wedge}" data-event-id="{html.escape(ev_id)}" data-week="{ev["week"]}" />'
            )
            triggered_drawn.append(
                f'<text class="choice-index" x="{cx:.1f}" y="{cy + 3:.1f}" '
                f'text-anchor="middle">{choice_index + 1}</text>'
            )
        triggered_drawn.append("</g>")

    return (
        f'<svg viewBox="0 0 {layout.width} {layout.height}" role="img" '
        f'aria-label="Full game decision graph for one playthrough">'
        + "".join(lane_bands)
        + "".join(lane_labels)
        + "".join(week_ticks)
        + f'<polyline class="agent-path" points="{path_points}" />'
        + "".join(edges)
        + "".join(all_event_dots)
        + "".join(triggered_drawn)
        + "</svg>"
    )


def render_decision_graph_page(
    *,
    report_dir: Path,
    run: dict,
    event_graph: dict,
    back_href: str = "../../index.html",
) -> str:
    """Render the standalone decision-graph page for one run."""
    payload = _decision_graph_payload(event_graph, run)
    svg = _decision_graph_svg(payload)
    triggered = payload["events"]
    # The full event pool (for the legend + lane counts) — we have to
    # reconstruct it from the layout that lives inside the payload.
    layout_obj: _GraphLayout = payload["layout"]
    triggered_events_full = layout_obj.events
    lane_order_for_legend = layout_obj.lane_order

    # Per-week timeline cells (for the scrubber)
    timeline_cells = []
    for week in range(0, payload["max_week"] + 1):
        triggered_at = next(
            (e for e in triggered if e["week"] == week), None
        )
        cls = "timeline-cell"
        if triggered_at:
            cls += " is-triggered"
        timeline_cells.append(
            f'<div class="{cls}" data-week="{week}" '
            f'data-event-id="{html.escape(triggered_at["event_id"]) if triggered_at else ""}">'
            f'<span class="w">{week}</span>'
            f'<span class="dot"></span>'
            f"</div>"
        )

    # Side-panel default = first triggered week
    default = triggered[0] if triggered else None
    default_block = ""
    if default:
        default_block = _render_choice_panel(default)

    # JSON payload for the JS interactivity
    json_payload = json.dumps(
        {
            "events": triggered,
            "all_event_ids": payload["all_event_ids"],
            "max_week": payload["max_week"],
        },
        ensure_ascii=False,
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Decision graph — run {payload['seed_display']} · {html.escape(payload['policy'])}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{_CSS}</style>
</head>
<body>
<header class="masthead">
  <span class="kicker"><a href="{html.escape(back_href)}">← Back to issue</a></span>
  <span class="issue-line">Decision graph · run seed {payload['seed_display']} · policy <em>{html.escape(payload['policy'])}</em></span>
  <span class="date">{html.escape(_byline_now())}</span>
</header>

<section class="cover">
  <div class="issue-meta">
    <span><strong>{payload['policy'] or '—'}</strong>policy<strong>played</strong></span>
    <span><strong>{len(triggered)}</strong>events<strong>triggered</strong></span>
    <span><strong>{payload['max_week']}</strong>weeks<strong>simulated</strong></span>
    <span><strong>{html.escape(payload['ending_id'] or 'unknown')}</strong>final<strong>ending</strong></span>
  </div>
  <h1>The decision <em>graph</em></h1>
  <p class="deck">
    Every event the engine could have triggered — drawn on a single canvas, one lane
    per <em>event_type</em> seen in the data, twenty weeks across. The terracotta line
    is the path this run actually took; the small numbered wedges are the choices
    the agent picked at each event. Click any node, any week, any choice — the rest
    of the page will follow.
  </p>
</section>

<main class="graph-shell">
  <div class="legend-row">
    {''.join(f'<span><span class="swatch {html.escape(name)}"></span>{html.escape(name)} event ({sum(1 for e in triggered_events_full if _lane_for_event(e) == name)})</span>' for name in lane_order_for_legend)}
    <span><span class="swatch path"></span>agent path</span>
    <span style="color:var(--accent);font-style:italic;font-family:var(--serif);font-size:13px">
      wedge numerals = the choice index the agent picked (1-indexed)
    </span>
  </div>

  <div class="graph-stage" id="graph-stage">
    {svg}
  </div>

  <div class="graph-footnote">
    Hover any node to see the event title and the choice the agent took.
    Use the week scrubber below to replay the path one week at a time — every step
    replays the highlight up to that point in the simulation.
  </div>

  {('<details class="graph-diagnostics" style="margin:18px 0 0;font-family:var(--mono);font-size:11px;line-height:1.55;color:var(--ink-soft)">'
    '<summary style="cursor:pointer;letter-spacing:0.16em;text-transform:uppercase;color:var(--ink-soft);padding:6px 0;border-top:1px dotted var(--rule);border-bottom:1px dotted var(--rule)">'
    'Adaptive diagnostics · ' + str(len(payload.get("diagnostics", []))) + ' note(s)'
    '</summary>'
    '<div style="padding:10px 14px;background:var(--paper-deep);border-left:2px solid var(--accent);margin-top:6px">'
    + ("".join("<div>· " + html.escape(d) + "</div>" for d in payload.get("diagnostics", []))
       or '<div style="color:var(--muted)">No schema adaptions were needed — payload parsed cleanly.</div>')
    + '</div></details>') if payload.get("diagnostics") is not None else ''}

  <div class="timeline-rail" id="timeline-rail">
    <div class="timeline-strip">
      {''.join(timeline_cells)}
    </div>
    <div class="timeline-controls">
      <div class="row">
        <button type="button" id="btn-play">▶ Play</button>
        <button type="button" id="btn-pause">⏸ Pause</button>
        <button type="button" id="btn-reset">⟲ Reset</button>
      </div>
      <div class="row">
        <span style="color:var(--ink-soft)">W</span>
        <input type="range" id="week-slider" min="0" max="{payload['max_week']}" value="0" step="1" />
        <span id="week-current" style="color:var(--accent);font-weight:600">0</span>
      </div>
      <div class="legend">
        <span>click any week</span>
        <span class="dot-line">drag slider</span>
      </div>
    </div>
  </div>

  <div class="graph-side-panel">
    <div>
      <article class="article" style="grid-template-columns:1fr;padding:32px 0;border-bottom:none">
        <div class="column">
          <h2 style="margin-top:0">What the agent did this week</h2>
          <div id="week-detail" style="font-family:var(--body);font-size:18px;line-height:1.6;color:var(--ink-soft)">
            Click a node on the graph or a week on the timeline to inspect the
            agent choice, its effects, and the state it left behind.
          </div>
        </div>
      </article>
    </div>
    <aside>
      <div class="panel-card" id="choice-panel">
        {default_block or '<h4>Pick a week</h4><div>Use the slider or click any node to start.</div>'}
      </div>
    </aside>
  </div>
</main>

<div class="graph-tooltip" id="graph-tooltip" role="tooltip"></div>

<footer class="colophon">
  <div class="row">
    <span>{html.escape(report_dir.name)} · seed {payload['seed'] or '—'} · policy {html.escape(payload['policy'])}</span>
    <span>Generated by tools/build_dashboard.py · decision-graph</span>
  </div>
</footer>

<script id="payload" type="application/json">{json_payload}</script>
<script>
(function() {{
  const payload = JSON.parse(document.getElementById('payload').textContent);
  const maxWeek = payload.max_week;
  const eventsByWeek = Object.fromEntries(payload.events.map(e => [e.week, e]));
  const eventsById = Object.fromEntries(payload.events.map(e => [e.event_id, e]));

  const stage = document.getElementById('graph-stage');
  const cells = document.querySelectorAll('.timeline-cell');
  const slider = document.getElementById('week-slider');
  const weekCurrent = document.getElementById('week-current');
  const choicePanel = document.getElementById('choice-panel');
  const weekDetail = document.getElementById('week-detail');
  const tooltip = document.getElementById('graph-tooltip');

  function setCurrent(week) {{
    week = Math.max(0, Math.min(maxWeek, week));
    slider.value = String(week);
    weekCurrent.textContent = String(week);

    // Highlight timeline cells up to and including `week`
    cells.forEach(cell => {{
      const w = Number(cell.dataset.week);
      cell.classList.toggle('is-current', w === week);
    }});

    // Highlight nodes whose week <= `week`
    document.querySelectorAll('.path-event-group').forEach(g => {{
      const w = Number(g.dataset.week);
      g.classList.toggle('is-current', w <= week);
    }});

    // Highlight edges whose start week < `week`
    document.querySelectorAll('.path-edge').forEach((e, i) => {{
      e.classList.toggle('is-current', i < week);
    }});

    // Update detail panel
    const ev = eventsByWeek[week];
    if (ev) {{
      weekDetail.innerHTML = renderWeekDetail(ev);
      choicePanel.innerHTML = renderChoicePanel(ev);
    }} else {{
      weekDetail.innerHTML = '<em style="color:var(--muted)">No event triggered in week ' + week + '. The agent took routine actions.</em>';
      choicePanel.innerHTML = '<h4>Week ' + week + '</h4><div style="color:var(--ink-soft)">No event. Routine actions only.</div>';
    }}
  }}

  function renderWeekDetail(ev) {{
    const actions = ev.selected_actions && ev.selected_actions.length
      ? ev.selected_actions.map(a => '<code>' + escape(a) + '</code>').join(' ')
      : '<em style="color:var(--muted)">no actions recorded</em>';
    const stateBits = Object.entries(ev.after_state || {{}}).slice(0, 6).map(
      ([k, v]) => '<span style="font-family:var(--mono);font-size:11px;color:var(--ink-soft)">' + escape(k) + ': ' + escape(String(v)) + '</span>'
    ).join(' · ');
    return `
      <p style="margin-top:0"><strong style="font-family:var(--mono);font-size:12px;color:var(--accent);letter-spacing:0.12em">W${{ev.week}} · ${{escape(ev.event_id)}}</strong></p>
      <p style="font-family:var(--serif);font-style:italic;font-size:22px;line-height:1.3;color:var(--ink);margin:6px 0">
        ${{escape(ev.title || ev.event_id)}}
      </p>
      <p style="font-size:14px">The agent picked choice <strong style="color:var(--accent)">#${{ev.choice_index + 1}}</strong>:
        <span style="font-style:italic">"${{escape(ev.choice_text || '(none)')}}"</span>
      </p>
      <p style="font-size:13px;color:var(--ink-soft);margin-top:14px"><strong>Actions this week:</strong> ${{actions}}</p>
      <p style="font-size:11px;color:var(--muted);font-family:var(--mono)">${{stateBits}}</p>
    `;
  }}

  function renderChoicePanel(ev) {{
    const effects = ev.choice_effects || {{}};
    const eff = Object.entries(effects).map(([k, v]) => {{
      const cls = Number(v) >= 0 ? 'pos' : 'neg';
      const sign = Number(v) >= 0 ? '+' : '';
      return `<span class="${{cls}}">${{escape(k)}} ${{sign}}${{escape(String(v))}}</span>`;
    }}).join('') || '<span style="color:var(--muted)">no effects recorded</span>';
    return `
      <h4>W${{ev.week}} · choice #${{ev.choice_index + 1}}</h4>
      <span class="pick-text">"${{escape(ev.choice_text || '(no text)')}}"</span>
      <p style="font-size:11px;color:var(--muted);font-family:var(--mono);letter-spacing:0.08em">${{escape(ev.event_id)}}</p>
      <h4 style="margin-top:14px">Effects</h4>
      <div class="effects">${{eff}}</div>
    `;
  }}

  function escape(s) {{
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }}

  // Wire up node clicks
  document.querySelectorAll('.path-event-group').forEach(g => {{
    const ev = eventsById[g.dataset.eventId];
    if (!ev) return;
    g.addEventListener('click', () => setCurrent(ev.week));
    g.addEventListener('mouseenter', e => showTooltip(ev, e));
    g.addEventListener('mousemove', moveTooltip);
    g.addEventListener('mouseleave', hideTooltip);
  }});

  // Wire up background event dots
  document.querySelectorAll('.event-node').forEach(n => {{
    if (!n.classList.contains('triggered')) return;
  }});

  // Wire timeline cells
  cells.forEach(cell => {{
    cell.addEventListener('click', () => setCurrent(Number(cell.dataset.week)));
  }});

  // Slider
  slider.addEventListener('input', () => setCurrent(Number(slider.value)));

  // Auto-play
  let playTimer = null;
  function play() {{
    if (playTimer) return;
    let w = Number(slider.value);
    playTimer = setInterval(() => {{
      if (w >= maxWeek) {{ stopPlay(); return; }}
      w++;
      setCurrent(w);
    }}, 700);
  }}
  function stopPlay() {{
    if (playTimer) {{ clearInterval(playTimer); playTimer = null; }}
  }}
  function resetPlay() {{
    stopPlay();
    setCurrent(0);
  }}
  document.getElementById('btn-play').addEventListener('click', play);
  document.getElementById('btn-pause').addEventListener('click', stopPlay);
  document.getElementById('btn-reset').addEventListener('click', resetPlay);

  function showTooltip(ev, mouseEvent) {{
    tooltip.innerHTML = `
      <span class="tt-event-id">${{escape(ev.event_id)}}</span>
      <span class="tt-event-title">${{escape(ev.title || ev.event_id)}}</span>
      <span style="font-size:11px;color:var(--muted)">W${{ev.week}} · ${{escape(ev.event_type)}}</span>
      <span class="tt-choice">
        <span class="pick">▸ choice #${{ev.choice_index + 1}}</span>
        <span class="text">"${{escape(ev.choice_text || '(no text)')}}"</span>
      </span>
    `;
    tooltip.classList.add('is-visible');
    moveTooltip(mouseEvent);
  }}
  function moveTooltip(e) {{
    const x = (e.clientX || 0) + 14;
    const y = (e.clientY || 0) + 14;
    tooltip.style.left = Math.min(window.innerWidth - 380, x) + 'px';
    tooltip.style.top = Math.min(window.innerHeight - 180, y) + 'px';
  }}
  function hideTooltip() {{ tooltip.classList.remove('is-visible'); }}

  // Initial state
  setCurrent(0);
}})();
</script>
</body>
</html>
"""


def _render_choice_panel(ev: dict) -> str:
    effects = ev.get("choice_effects") or {}
    eff_html = "".join(
        f'<span class="{("pos" if float(v) >= 0 else "neg")}">{html.escape(str(k))} '
        f'{("+" if float(v) >= 0 else "")}{html.escape(str(v))}</span>'
        for k, v in effects.items()
    ) or '<span style="color:var(--muted)">no effects recorded</span>'
    return (
        f"<h4>W{ev['week']} · choice #{ev['choice_index'] + 1}</h4>"
        f'<span class="pick-text">"{html.escape(ev.get("choice_text") or "(no text)")}"</span>'
        f'<p style="font-size:11px;color:var(--muted);font-family:var(--mono);letter-spacing:0.08em">'
        f"{html.escape(ev.get('event_id', ''))}</p>"
        f"<h4 style='margin-top:14px'>Effects</h4>"
        f"<div class='effects'>{eff_html}</div>"
    )


def render_front_page(issues: list[Issue]) -> str:
    total_runs, total_anomalies, total_critical, total_findings = _fmt_run_kpis(issues)
    issue_cards = []
    for idx, issue in enumerate(issues[:24], start=1):
        top_ending = issue.endings[0]["ending_id"] if issue.endings else "—"
        top_rate = issue.endings[0]["rate"] if issue.endings else "—"
        anomaly_total = len(issue.anomalies)
        severity = "info"
        for a in issue.anomalies:
            s = str(a.get("severity", ""))
            if s == "critical":
                severity = "critical"
                break
            if s == "warning" and severity != "critical":
                severity = "warning"
        issue_cards.append(
            f"<a class='issue-card fade-in d{idx % 3}' href='browse/{issue.issue_kind}/{issue.issue_id}/index.html'>"
            f"<span class='issue-num'>№ {idx:03d} · {issue.issue_kind.upper()}</span>"
            f"<h3>{_highlight(issue.title)}</h3>"
            f"<div class='deck'>{html.escape(issue.subtitle)}</div>"
            f"<div class='stats'>"
            f"<span>runs<strong>{issue.total_runs}</strong></span>"
            f"<span>top end.<br><strong style='font-size:13px'>{html.escape(top_ending[:18])}</strong></span>"
            f"<span>anom.<br><strong>{anomaly_total}</strong></span>"
            f"</div>"
            f"<div style='margin-top:10px'><span class='severity {severity}'>{severity}</span>"
            f"<span style='font-family:var(--mono);font-size:11px;color:var(--muted);letter-spacing:0.1em;'>ENDING DISTRIBUTION · {html.escape(top_rate)}</span>"
            f"</div>"
            f"</a>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>The Analytical Review — game_analysis_agent</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{_CSS}</style>
</head>
<body>
<header class="masthead">
  <span class="kicker">Vol. 0.2 · Field reports</span>
  <span class="issue-line">No. ∞ · A continuous publication</span>
  <span class="date">{datetime.now(tz=UTC).strftime('%a %d %b %Y · %H:%M UTC')}</span>
</header>
<section class="banner">
  <div class="banner-inner">
    <div>
      <h1>The Analytical<br><span class="accent"><em>Review</em></span></h1>
      <p class="deck" style="margin-top:22px">A field journal from the <em>study-in-germany</em> development pipeline —
      where <span style="font-family:var(--mono);font-size:14px;letter-spacing:0.06em">godot</span>
      runs ten thousand weeks, Python finds the rules the engine forgot,
      and seven language models argue about which ending feels earned.</p>
    </div>
    <div class="meta-col">
      <strong style="font-size:64px;line-height:0.9;font-family:var(--serif);font-variation-settings:'opsz' 144,'wght' 480,'WONK' 1">{len(issues):02d}</strong>
      <span style="display:block;margin-top:6px">issues in print</span>
    </div>
  </div>
</section>

<main>
  <div class="section-rule"><span class="num">§I</span><span class="label">The numbers that didn't lie</span></div>
  <div class="kpi-strip">
    <div class="kpi"><span class="num">{total_runs}</span><span class="label">Total weeks simulated</span></div>
    <div class="kpi"><span class="num"><em>{total_anomalies}</em></span><span class="label">Anomalies surfaced</span><span class="delta">{total_critical} critical</span></div>
    <div class="kpi"><span class="num">{total_findings}</span><span class="label">Tuning findings</span></div>
    <div class="kpi"><span class="num"><em>{len(issues)}</em></span><span class="label">Issues printed</span></div>
  </div>

  <div class="section-rule"><span class="num">§II</span><span class="label">In this edition — issues to read cover-to-cover</span></div>
  <div class="issue-shelf">
    {''.join(issue_cards)}
  </div>

  <div class="byline-rule" style="margin-top:64px">Game Analysis Agent · Reports Index · {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M UTC')}</div>
</main>

<footer class="colophon">
  <div class="row">
    <span>Set in Fraunces & Newsreader</span>
    <span>Editorial direction: editorial / data-journalism</span>
    <span>Generated by tools/build_dashboard.py</span>
  </div>
</footer>
</body>
</html>
"""


def _highlight(title: str) -> str:
    """Italicise occasional words in the title for editorial flavour."""
    out = html.escape(title)
    out = re.sub(r"\b(critical|cohort|overpick|underuse|route|probe|boundary)\b", r"<em>\1</em>", out, flags=re.I)
    return out


def render_issue(issue: Issue) -> str:
    body_agents = [
        ("Agent diagnosis", issue.agent_diagnosis_md),
        ("Tuning proposal", issue.tuning_proposal_md),
        ("Bug diagnosis", issue.bug_diagnosis_md),
        ("Value review", issue.value_review_md),
        ("Boundary report", issue.boundary_report_md),
        ("Content issues", issue.content_issues_md),
        ("Event graph report", issue.event_graph_report_md),
        ("Bugs summary", issue.bugs_summary_md),
    ]

    sections: list[str] = []
    for label, md in body_agents:
        if not md.strip():
            continue
        rendered = render_markdown(md)
        sections.append(
            f"<article class='article fade-in'>"
            f"<div class='column'>{rendered}</div>"
            f"<aside class='marginalia'><h4>{html.escape(label)}</h4>"
            f"<div style='font-family:var(--mono);font-size:11px;color:var(--muted);line-height:1.4'>"
            f"{len(md)} chars · rendered as editorial column</div></aside>"
            f"</article>"
        )

    ending_table = ""
    if issue.endings:
        rows = "".join(
            f"<tr><td>{html.escape(row['policy'])}</td><td>{html.escape(row['ending_id'])}</td>"
            f"<td class='right'>{row['count']}</td>"
            f"<td class='right'>"
            f"<span class='bar' style='width:{int(float(row['rate'])*80)}px'></span>{row['rate']}"
            f"</td></tr>"
            for row in issue.endings
        )
        ending_table = (
            "<div class='endgrid'>"
            "<div>"
            "<h3 style='font-family:var(--serif);font-style:italic;font-size:32px;"
            "font-variation-settings:\"opsz\" 96, \"wght\" 380, \"SOFT\" 100;margin:0 0 12px'>"
            "Where the runs came to rest</h3>"
            "<div class='endtable'><table>"
            "<thead><tr><th>policy</th><th>ending</th><th class='right'>n</th><th class='right'>rate</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></div>"
            "</div>"
            "<div>"
            "<h3 style='font-family:var(--serif);font-style:italic;font-size:32px;"
            "font-variation-settings:\"opsz\" 96, \"wght\" 380, \"SOFT\" 100;margin:0 0 12px'>"
            "Actions at the top of the heap</h3>"
            "<div class='endtable'><table>"
            "<thead><tr><th>policy</th><th>action_id</th><th class='right'>n</th><th class='right'>rate/run</th></tr></thead>"
            + "".join(
                f"<tr><td>{html.escape(row['policy'])}</td><td>{html.escape(row['action_id'])}</td>"
                f"<td class='right'>{row['count']}</td><td class='right'>{row['rate_per_run']}</td></tr>"
                for row in issue.top_actions
            )
            + "</tbody></table></div>"
            "</div>"
            "</div>"
        )

    spark_blocks = []
    interesting_metrics = [
        ("stress", "var(--accent)", 0),
        ("hunger", "var(--warn)", 1),
        ("money", "var(--forest)", 2),
        ("academic_progress", "var(--ink)", 3),
    ]
    for metric, color, delay in interesting_metrics:
        block = _spark_block_for_metric(issue, metric, color=color, delay=delay)
        if block:
            spark_blocks.append(block)
    spark_section = ""
    if spark_blocks:
        spark_section = (
            "<article class='article fade-in'>"
            "<div class='column'>"
            "<h2 style='font-family:var(--serif);font-style:italic;font-size:44px;"
            "font-variation-settings:\"opsz\" 144, \"wght\" 360, \"SOFT\" 100;margin-top:0'>"
            "Pulse of the simulation</h2>"
            "<p class='deck' style='font-style:italic;color:var(--ink-soft);font-size:18px'>"
            "Four metrics, drawn week by week. Solid line is the cohort mean. "
            "Click any axis label to drill into the raw weekly_stats.csv.</p>"
            f"<div style='display:grid;grid-template-columns:repeat(2,1fr);gap:18px'>{''.join(spark_blocks)}</div>"
            "</div>"
            "<aside class='marginalia'>"
            "<h4>How to read</h4>"
            "<p style='font-family:var(--mono);font-size:11px;color:var(--ink-soft);"
            "line-height:1.5;margin:0'>Each sparkline draws on load via CSS stroke-dashoffset animation. "
            "Dot at the right edge marks the final week's mean.</p>"
            "<h4>Raw stats</h4>"
            f"<div style='font-family:var(--mono);font-size:11px;color:var(--ink-soft);line-height:1.6'>"
            f"weekly_metrics: {len(issue.weekly_metrics)}<br>"
            f"weeks recorded: {len({p.week for p in issue.weekly_series})}<br>"
            f"raw_runs.jsonl: {issue.raw_runs_count} runs"
            f"</div>"
            "</aside>"
            "</article>"
        )

    value_table_section = ""
    if issue.value_findings:
        value_table_section = (
            "<article class='article fade-in'>"
            "<div class='column'>"
            "<h2 style='font-family:var(--serif);font-style:italic;font-size:36px;"
            "font-variation-settings:\"opsz\" 96, \"wght\" 360, \"SOFT\" 100;margin-top:0'>"
            "What the number nerds found</h2>"
            f"{_top_findings_table(issue.value_findings, limit=8)}"
            "</div>"
            "<aside class='marginalia'>"
            f"{_anomaly_marginalia(issue)}"
            f"{_top_findings_table(issue.route_findings, limit=5)}"
            "</aside>"
            "</article>"
        )

    playthrough_section = ""
    if issue.playthrough:
        playthrough_section = (
            "<article class='article fade-in'>"
            "<div class='column'>"
            "<h2 style='font-family:var(--serif);font-style:italic;font-size:36px;"
            "font-variation-settings:\"opsz\" 96, \"wght\" 360, \"SOFT\" 100;margin-top:0'>"
            "An LLM at the wheel</h2>"
            "<p class='deck' style='font-style:italic;color:var(--ink-soft);font-size:18px'>"
            "One playthrough, twenty weeks, the LLM calling its own shots. "
            "Each dot on the spine is a decision; red dots are weeks that tripped an anomaly.</p>"
            f"{_playthrough_spine(issue)}"
            "</div>"
            "<aside class='marginalia'>"
            "<h4>Playthrough summary</h4>"
            "<div style='font-family:var(--mono);font-size:11px;color:var(--ink-soft);line-height:1.5'>"
            f"<pre style='white-space:pre-wrap;font-family:var(--mono);background:transparent;"
            f"padding:0;font-size:11px;color:var(--ink-soft);margin:0'>"
            f"{html.escape(issue.playthrough_summary_md[:1200])}</pre>"
            "</div></aside></article>"
        )

    gate_summary = ""
    if issue.gate_report:
        passed = bool(issue.gate_report.get("passed"))
        failures = issue.gate_report.get("failures", []) or issue.gate_report.get("violations", [])
        failures_text = ", ".join(
            (f.get("gate") if isinstance(f, dict) else str(f)) for f in failures
        )[:200]
        if passed or not failures:
            gate_summary = "<div class='gate-pass'>GATE PASS — every check honoured</div>"
        else:
            gate_summary = (
                f"<div class='gate-fail'>GATE FAIL — {len(failures)} violation(s): "
                f"{html.escape(failures_text)}</div>"
            )

    manifest_block = ""
    if issue.manifest:
        trace = issue.manifest.get("trace", {}) if isinstance(issue.manifest, dict) else {}
        manifest_block = (
            "<div class='gate-pass' style='border-color:var(--ink);color:var(--ink)'>"
            f"TRACEABLE REPORT — run_id "
            f"<strong>{html.escape(str(issue.manifest.get('run_id', issue.issue_id)))}</strong>"
            f" · manifest <strong>report_manifest.json</strong>"
            f" · trace <strong>{html.escape(str(trace.get('primary_file', '')))}</strong>"
            "</div>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(issue.title)} — The Analytical Review</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{_CSS}</style>
</head>
<body>
<header class="masthead">
  <span class="kicker"><a href="../../index.html">← Front Page</a></span>
  <span class="issue-line">Issue · {html.escape(issue.issue_id)}</span>
  <span class="date">{html.escape(issue.byline)}</span>
</header>

<section class="cover">
  <div class="issue-meta">
    <span><strong>{issue.total_runs}</strong>runs<strong>simulated</strong></span>
    <span><strong>{len(issue.scenarios)}</strong>scenarios<strong>covered</strong></span>
    <span><strong>{len(issue.policies)}</strong>policies<strong>compared</strong></span>
    <span><strong>{len(issue.anomalies)}</strong>anomalies<strong>surfaced</strong></span>
  </div>
  <h1>{_highlight(issue.title)}</h1>
  <p class="deck">{html.escape(issue.subtitle)}</p>
  {manifest_block}
  {gate_summary}
</section>

<nav class="tab-rail fade-in">
  <a href="#ending-grid">Findings</a>
  <a href="#spark-section">Pulse</a>
  <a href="#value-section">Value findings</a>
  <a href="#playthrough-section">Playthrough</a>
  <a href="#agent-section">Agent columns</a>
</nav>

<main>
  {ending_table}
  {spark_section}
  {value_table_section}
  {playthrough_section}
  {''.join(sections)}
</main>

<footer class="colophon">
  <div class="row">
    <span>{html.escape(issue.issue_kind).upper()} issue · {html.escape(issue.slug)}</span>
    <span>Generated by tools/build_dashboard.py</span>
  </div>
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_dashboard")
    sub = parser.add_subparsers(dest="cmd", required=False)

    # Default mode: build the dashboard from --reports.
    p_all = sub.add_parser("all", help="Build front page + per-issue pages (default).")
    p_all.add_argument(
        "--reports",
        type=Path,
        default=DEFAULT_REPORTS,
        help="Root directory containing reports/{balance,boundary,play}/",
    )
    p_all.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory for per-issue pages. Defaults to <reports>/browse.",
    )

    # Decision-graph mode: render one full decision graph for one run.
    p_dg = sub.add_parser(
        "decision-graph",
        help="Render the full-event decision graph with one run highlighted.",
    )
    p_dg.add_argument(
        "--report-dir",
        type=Path,
        required=True,
        help="Path to a balance report dir (e.g. reports/balance/<run>).",
    )
    p_dg.add_argument(
        "--run-id",
        type=int,
        default=0,
        help="Run id within raw_runs.jsonl to highlight (default: 0).",
    )
    p_dg.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory. Defaults to <report-dir>/decision_graph/<run_id>/.",
    )
    p_dg.set_defaults(func=cmd_decision_graph)

    # Emit just the React frontend's JSON data feed (without rebuilding
    # every static HTML page). Useful when iterating on the React app.
    p_emit = sub.add_parser(
        "emit-frontend-manifest",
        help="Emit only the JSON manifest consumed by the React frontend.",
    )
    p_emit.add_argument(
        "--reports",
        type=Path,
        default=DEFAULT_REPORTS,
    )
    p_emit.add_argument(
        "--frontend-public",
        type=Path,
        default=None,
        help="If set, mirror manifest.json + browse/ into this directory.",
    )
    p_emit.set_defaults(func=cmd_emit_frontend_manifest)

    p_all.set_defaults(func=cmd_all)
    parser.set_defaults(func=cmd_all)
    return parser


def _emit_decision_graph_for(
    *,
    browse_root: Path,
    report_dir: Path,
    issue_id: str,
    back_href: str,
    run_id: int = 0,
) -> bool:
    """Render one decision-graph page + diagnostics. Returns True on success."""
    if not (report_dir / "raw_runs.jsonl").exists():
        return False
    if not (report_dir / "event_graph.json").exists():
        return False
    runs = _load_jsonl(report_dir / "raw_runs.jsonl")
    if not runs:
        return False
    event_graph = _load_json(report_dir / "event_graph.json") or {}
    if not event_graph.get("events"):
        return False
    target = next(
        (r for r in runs if int(r.get("run_id", -1)) == run_id),
        runs[0],
    )
    payload = _decision_graph_payload(event_graph, target)
    dg_dir = browse_root / "decision_graph" / issue_id / str(run_id)
    dg_dir.mkdir(parents=True, exist_ok=True)
    (dg_dir / "index.html").write_text(
        render_decision_graph_page(
            report_dir=report_dir,
            run=target,
            event_graph=event_graph,
            back_href=back_href,
        ),
        encoding="utf-8",
    )
    _write_diagnostics_json(
        dg_dir,
        event_graph=event_graph,
        payload=payload,
        raw_runs_path=report_dir / "raw_runs.jsonl",
        event_graph_path=report_dir / "event_graph.json",
    )
    return True


def _inject_dg_link(page_html: str, *, dg_link: str) -> str:
    """Inject a 'View the decision graph' link into the per-issue page tab rail."""
    marker = '<a href="#playthrough-section">Playthrough</a>'
    addition = (
        f'<a href="{dg_link}" style="margin-left:auto;background:var(--accent);color:var(--paper);'
        f'border-bottom-color:var(--accent-deep)">↗ Decision Graph</a>'
    )
    if marker in page_html and addition not in page_html:
        return page_html.replace(marker, marker + addition, 1)
    return page_html


def _write_diagnostics_json(
    out_dir: Path,
    *,
    event_graph: dict,
    payload: dict,
    raw_runs_path: Path,
    event_graph_path: Path,
) -> None:
    """Write ``_diagnostics.json`` next to the page.

    Captures what the adaptive layout discovered about the upstream data —
    new event types, dropped triggered events, unparseable choice_ids —
    so a human can see exactly what changed when the event tree evolves.
    """
    event_types = sorted({
        _lane_for_event(ev) for ev in event_graph.get("events") or [] if isinstance(ev, dict)
    })
    triggered_ids = {e.get("event_id") for e in payload.get("events", [])}
    graph_ids = {
        ev.get("id") for ev in event_graph.get("events") or [] if isinstance(ev, dict)
    }
    payload_diagnostics = payload.get("diagnostics", []) or []
    diagnostics = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "inputs": {
            "raw_runs": _display_path(raw_runs_path),
            "event_graph": _display_path(event_graph_path),
        },
        "event_graph_summary": {
            "total_events": len(event_graph.get("events") or []),
            "event_types": event_types,
            "lane_order": payload.get("lane_order", event_types),
        },
        "triggered_summary": {
            "count": len(payload.get("events", [])),
            "max_week_used": payload.get("max_week"),
            "ending_id": payload.get("ending_id"),
        },
        "adaptations": {
            "triggered_but_missing_in_graph": sorted(
                triggered_ids - graph_ids
            ),
            "diagnostics_notes": payload_diagnostics,
        },
    }
    (out_dir / "_diagnostics.json").write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _display_path(path: Path) -> str:
    """Return a compact path when it is inside the repo, otherwise absolute."""
    if path.is_absolute() and path.exists():
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)
    return str(path)


def cmd_all(args) -> int:
    reports: Path = args.reports.resolve()
    if not reports.exists():
        print(f"--reports does not exist: {reports}", file=sys.stderr)
        return 2
    front = reports / "index.html"
    browse_root: Path = (args.out or (reports / "browse")).resolve()
    issues = _discover_issues(reports)
    front.write_text(render_front_page(issues), encoding="utf-8")

    for issue in issues:
        target_dir = browse_root / issue.issue_kind / issue.issue_id
        target_dir.mkdir(parents=True, exist_ok=True)
        page_html = render_issue(issue)
        report_dir = reports / issue.issue_kind / issue.issue_id
        if (
            issue.issue_kind in ("balance", "play")
            and (report_dir / "raw_runs.jsonl").exists()
            and _emit_decision_graph_for(
                browse_root=browse_root,
                report_dir=report_dir,
                issue_id=issue.issue_id,
                back_href=f"../../{issue.issue_kind}/{issue.issue_id}/index.html",
            )
        ):
            page_html = _inject_dg_link(
                page_html,
                dg_link=f"decision_graph/{issue.issue_id}/0/index.html",
            )
        (target_dir / "index.html").write_text(page_html, encoding="utf-8")

    # Emit the React frontend's data feed (manifest.json + per-issue
    # bundles). Idempotent — running this on every dashboard build means
    # the Vite app always has fresh data.
    try:
        from emit_manifest import emit_all as _emit_manifest_all

        _emit_manifest_all(reports)
    except Exception as exc:
        print(f"manifest emit failed: {exc}", file=sys.stderr)

    print(f"Wrote {front} (front page)")
    print(f"Wrote {len(issues)} issue pages under {browse_root}")
    return 0


def cmd_emit_frontend_manifest(args) -> int:
    """Sub-command: write the JSON feed the React frontend consumes.

    Useful when iterating on the React app without rebuilding every
    static HTML page. Pair with:

        python tools/build_dashboard.py emit-frontend-manifest \
          --reports reports \
          --frontend-public frontend/public
    """
    from emit_manifest import emit_all as _emit_manifest_all

    _emit_manifest_all(args.reports)
    if args.frontend_public:
        target = args.frontend_public
        target.mkdir(parents=True, exist_ok=True)
        # Mirror the manifest tree: manifest.json + browse/...
        src_root = args.reports.resolve()
        # Copy manifest.json
        src = src_root / "manifest.json"
        if src.exists():
            (target / "manifest.json").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        # Mirror browse/
        browse_src = src_root / "browse"
        if browse_src.exists():
            browse_dst = target / "browse"
            browse_dst.mkdir(parents=True, exist_ok=True)
            for path in browse_src.rglob("manifest.json"):
                rel = path.relative_to(browse_src)
                dst = browse_dst / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            for path in browse_src.rglob("_diagnostics.json"):
                rel = path.relative_to(browse_src)
                dst = browse_dst / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Mirrored manifest into {target}/")
    return 0


def cmd_decision_graph(args) -> int:
    report_dir: Path = args.report_dir.resolve()
    if not report_dir.exists():
        print(f"--report-dir does not exist: {report_dir}", file=sys.stderr)
        return 2
    raw_runs_path = report_dir / "raw_runs.jsonl"
    event_graph_path = report_dir / "event_graph.json"
    if not raw_runs_path.exists():
        print(f"missing raw_runs.jsonl under {report_dir}", file=sys.stderr)
        return 3
    if not event_graph_path.exists():
        print(f"missing event_graph.json under {report_dir}", file=sys.stderr)
        return 4
    runs = _load_jsonl(raw_runs_path)
    event_graph = _load_json(event_graph_path) or {}
    target_run = next(
        (r for r in runs if int(r.get("run_id", -1)) == args.run_id),
        runs[0] if runs else None,
    )
    if target_run is None:
        print("no runs found", file=sys.stderr)
        return 5
    out_dir: Path = (args.out or (report_dir / "decision_graph" / str(args.run_id))).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = _decision_graph_payload(event_graph, target_run)
    html_doc = render_decision_graph_page(
        report_dir=report_dir,
        run=target_run,
        event_graph=event_graph,
        back_href=str(Path("..") / ".." / "balance" / report_dir.name / "index.html"),
    )
    (out_dir / "index.html").write_text(html_doc, encoding="utf-8")
    _write_diagnostics_json(
        out_dir,
        event_graph=event_graph,
        payload=payload,
        raw_runs_path=raw_runs_path,
        event_graph_path=event_graph_path,
    )
    print(f"Wrote {out_dir / 'index.html'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


__all__ = [
    "build_parser",
    "main",
    "render_front_page",
    "render_issue",
    "render_markdown",
]


if __name__ == "__main__":
    raise SystemExit(main())
