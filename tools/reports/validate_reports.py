#!/usr/bin/env python3
"""Validate the ``reports/`` directory against the locked layout.

See ``docs/operations/REPORTS_FORMAT.md`` for the contract this script
enforces. The validator walks the configured root and, for each
top-level subdirectory, checks:

* The subdirectory is in the locked layout (or, with ``--strict``,
  the script fails the run).
* For layouts that require a manifest, the manifest file exists and
  its ``schema_version`` matches the locked string in ``SCHEMAS``.
* For layouts with a required file inventory, every required file
  exists.

The script exits 0 on success and 1 on the first violation (unless
``--no-fail-fast`` is passed). ``--json`` emits a JSON line per
directory so CI can surface every issue at once.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORTS = ROOT / "reports"

# Top-level directories that are part of the latest-standard layout.
LOCKED_LAYOUT: frozenset[str] = frozenset(
    {
        "inference-ab",
        "persona-campaigns",
        "persona-runtime",
        "playtests",
        "repair-experiments",
        "private-local-vllm",
    }
)

# Per-layout rules. Each entry is ``(selector, manifest, required_files)``:
# * ``selector`` matches a directory name in the layout. ``""`` is the
#   catch-all (must be the last rule for the layout to be useful).
#   Selectors that aren't the catch-all also match any directory whose
#   name contains the selector.
# * ``manifest`` is either ``None`` (no manifest check) or a
#   ``(filename, schema_version)`` tuple.
# * ``required_files`` is a tuple of paths relative to the directory.
#   Use ``"public"`` to require the subdirectory itself, and
#   ``"public/foo.json"`` to require a file inside it.
RuleEntry = tuple[str, tuple[str, str] | None, tuple[str, ...]]
RULES: dict[str, tuple[RuleEntry, ...]] = {
    "inference-ab": (
        (
            "",
            ("manifest.json", "inference-ab-report-manifest-v1"),
            (
                "manifest.json",
                "summary.json",
                "summary.csv",
                "requests.jsonl",
                "server-metrics.jsonl",
                "gpu-metrics.csv",
                "comparison.html",
            ),
        ),
        (
            "smoke",
            None,
            ("diagnostic-apc.jsonl", "diagnostic-apc.summary.json"),
        ),
        (
            "fixtures",
            None,
            ("persona-chat-trace.jsonl", "trace-capture-timing.json"),
        ),
    ),
    "persona-campaigns": (
        (
            "",
            ("campaign_manifest.json", "persona-campaign-manifest-v1"),
            (
                "campaign_manifest.json",
                "campaign_run_summary.json",
                "public",
                "public/campaign_manifest.json",
                "public/campaign_summary.json",
                "public/agent_eval.jsonl",
                "public/persona_runs.jsonl",
                "public/llm_calls.jsonl",
                "public/failure_clusters.json",
                "public/gate_report.json",
                "public/repair_eligibility.json",
            ),
        ),
    ),
    "repair-experiments": (
        (
            "",
            None,
            (
                "public",
                "public/gate_report.json",
                "public/repair_experiment.json",
                "public/comparison.json",
                "public/repair_summary.md",
            ),
        ),
        (
            "public",
            ("gate_report.json", "repair-bundle-gate-v1"),
            (
                "gate_report.json",
                "repair_experiment.json",
                "comparison.json",
                "repair_summary.md",
            ),
        ),
    ),
    "persona-runtime": (
        (
            "game",
            None,
            (
                ".playtest-forge-runtime-overlay.json",
                ".playtest-forge-source.json",
            ),
        ),
        (
            "",
            None,
            (".playtest-forge-source.json",),
        ),
    ),
    "playtests": (),
    "private-local-vllm": (),
}


@dataclass
class Issue:
    severity: str  # "error" or "warning"
    message: str


@dataclass
class Report:
    layout: str
    path: str
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def to_jsonable(self) -> dict[str, object]:
        return {
            "layout": self.layout,
            "path": self.path,
            "ok": self.ok,
            "issues": [
                {"severity": issue.severity, "message": issue.message}
                for issue in self.issues
            ],
        }


def _read_manifest_version(manifest_path: Path) -> str | None:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    version = payload.get("schema_version")
    return version if isinstance(version, str) else None


def _select_rule(layout: str, directory_name: str) -> RuleEntry | None:
    """Pick the first rule whose selector matches the directory name.

    A selector of ``""`` is the catch-all (must be the last rule for
    the layout to be useful). Non-empty selectors match when the
    directory name equals them or contains them as a substring.
    """

    rules = RULES.get(layout, ())
    for entry in rules:
        selector = entry[0]
        if not selector:
            continue
        if directory_name == selector or selector in directory_name:
            return entry
    for entry in rules:
        if entry[0] == "":
            return entry
    return None


def _read_submittable_flag(directory: Path) -> bool | None:
    """Read the ``submittable`` flag from a persona campaign's run summary.

    Returns ``None`` if the file is missing or unparseable.
    """

    summary_path = directory / "campaign_run_summary.json"
    if not summary_path.exists():
        return None
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = payload.get("submittable")
    return value if isinstance(value, bool) else None


def _check_directory(
    layout: str,
    directory: Path,
    reports_root: Path,
    rel: callable[[Path], str],
    *,
    strict: bool,
) -> Report:
    report = Report(layout=layout, path=rel(directory))

    rule = _select_rule(layout, directory.name)
    if rule is None:
        if strict and layout not in LOCKED_LAYOUT:
            report.issues.append(
                Issue(
                    "error",
                    f"top-level layout '{layout}' is not in the locked layout",
                )
            )
        return report

    _, schema_spec, required_files = rule
    if schema_spec is not None:
        manifest_name, required_version = schema_spec
        manifest_path = directory / manifest_name
        if not manifest_path.exists():
            report.issues.append(
                Issue(
                    "error",
                    f"missing required manifest '{manifest_name}' (expected schema '{required_version}')",
                )
            )
        else:
            actual_version = _read_manifest_version(manifest_path)
            if actual_version != required_version:
                report.issues.append(
                    Issue(
                        "error",
                        f"manifest '{manifest_name}' schema_version is {actual_version!r}, expected {required_version!r}",
                    )
                )

    # For persona campaigns with a non-submittable run summary, the
    # public/ bundle is intentionally absent — the campaign never
    # passed the gate. Demote the missing public/* entries to a
    # warning so the validator reflects the audit trail instead of
    # flagging the failed run as malformed.
    optional_prefix = "public/"
    is_non_submittable_campaign = (
        layout == "persona-campaigns"
        and _read_submittable_flag(directory) is False
    )

    for relative in required_files:
        if is_non_submittable_campaign and (
            relative == "public" or relative.startswith(optional_prefix)
        ):
            candidate = directory / relative
            if not candidate.exists():
                report.issues.append(
                    Issue(
                        "warning",
                        f"missing public/ bundle '{rel(candidate)}' "
                        f"(campaign is submittable=false; bundle intentionally absent)",
                    )
                )
            continue
        candidate = directory / relative
        if not candidate.exists():
            label = "subdirectory" if candidate.suffix == "" else "file"
            report.issues.append(
                Issue(
                    "error",
                    f"missing required {label} '{rel(candidate)}'",
                )
            )

    if strict and layout not in LOCKED_LAYOUT:
        report.issues.append(
            Issue("error", f"top-level layout '{layout}' is not in the locked layout")
        )

    return report


def _check_top_level(
    entry: Path,
    reports_root: Path,
    rel: callable[[Path], str],
    *,
    strict: bool,
) -> list[Report]:
    if not entry.is_dir():
        return []

    layout = entry.name
    if layout not in RULES:
        report = Report(layout=layout, path=rel(entry))
        if strict:
            report.issues.append(
                Issue("error", f"top-level layout '{layout}' is not in the locked layout")
            )
        else:
            report.issues.append(
                Issue(
                    "warning",
                    f"top-level layout '{layout}' is not validated; pass --strict to fail on it",
                )
            )
        return [report]

    return [
        _check_directory(layout, child, reports_root, rel, strict=strict)
        for child in sorted(entry.iterdir())
        if child.is_dir()
    ]


def collect_reports(reports_root: Path, *, strict: bool) -> list[Report]:
    if not reports_root.exists():
        return [
            Report(
                layout="(root)",
                path=str(reports_root),
                issues=[Issue("error", f"reports root {reports_root} does not exist")],
            )
        ]

    def _rel(path: Path) -> str:
        try:
            return str(path.relative_to(reports_root))
        except ValueError:
            return str(path)

    reports: list[Report] = []
    for entry in sorted(reports_root.iterdir()):
        reports.extend(_check_top_level(entry, reports_root, _rel, strict=strict))
    return reports


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_REPORTS,
        help="Path to the reports root (default: ./reports).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on top-level directories that are not in the locked layout.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit one JSON record per directory and skip the human summary.",
    )
    parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="Continue past the first error so the JSON output covers every directory.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    reports = collect_reports(args.root, strict=args.strict)

    if args.json:
        for report in reports:
            print(json.dumps(report.to_jsonable()))

    if not reports:
        if not args.json:
            print(f"No report directories found under {args.root}.")
        return 0

    failures = [report for report in reports if not report.ok]
    if not args.json:
        for report in reports:
            if not report.issues:
                print(f"  OK   {report.path}")
                continue
            for issue in report.issues:
                marker = "ERR " if issue.severity == "error" else "WARN"
                print(f"  {marker}  {report.path}: {issue.message}")
        print()
        print(
            f"Validated {len(reports)} directories; "
            f"{len(failures)} with errors."
        )

    if failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
