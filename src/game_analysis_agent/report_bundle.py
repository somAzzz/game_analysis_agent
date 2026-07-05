from __future__ import annotations

from pathlib import Path


DEFAULT_REPORT_FILES = [
    "summary.json",
    "ending_distribution.csv",
    "weekly_stats.csv",
    "action_pick_rates.csv",
    "event_trigger_rates.csv",
    "choice_pick_rates.csv",
    "anomaly_report.md",
]


def read_report_bundle(report_dir: str | Path, files: list[str] | None = None) -> str:
    directory = Path(report_dir)
    selected_files = files or DEFAULT_REPORT_FILES
    parts: list[str] = []

    for name in selected_files:
        path = directory / name
        if not path.exists():
            parts.append(f"## {name}\n\nMISSING\n")
            continue
        parts.append(f"## {name}\n\n```text\n{path.read_text(encoding='utf-8')}\n```\n")

    return "\n".join(parts)


def render_prompt(template_path: str | Path, report_bundle: str) -> str:
    template = Path(template_path).read_text(encoding="utf-8")
    return template.replace("{{REPORT_BUNDLE}}", report_bundle)
