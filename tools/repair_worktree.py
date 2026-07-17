#!/usr/bin/env python3
"""Create an isolated repair worktree or validate/save its committed patch."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.repair_experiment import RepairExperimentPlan  # noqa: E402
from game_analysis_agent.repair_worktree import (  # noqa: E402
    RepairWorktreeError,
    create_repair_worktree,
    validate_and_save_patch,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--source-repository", type=Path, required=True)
    create.add_argument("--destination", type=Path, required=True)
    create.add_argument("--baseline-commit", required=True)
    create.add_argument("--branch", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--worktree", type=Path, required=True)
    validate.add_argument("--plan", type=Path, required=True)
    validate.add_argument("--patch", type=Path, required=True)
    validate.add_argument("--evidence", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "create":
            path = create_repair_worktree(
                source_repository=args.source_repository,
                destination=args.destination,
                baseline_commit=args.baseline_commit,
                branch=args.branch,
            )
            payload = {"status": "created", "worktree": str(path)}
        else:
            plan = RepairExperimentPlan.model_validate_json(
                args.plan.read_text(encoding="utf-8")
            )
            evidence = validate_and_save_patch(
                worktree=args.worktree,
                plan=plan,
                patch_path=args.patch,
                project_root=ROOT,
            )
            args.evidence.parent.mkdir(parents=True, exist_ok=True)
            args.evidence.write_text(
                evidence.model_dump_json(indent=2) + "\n", encoding="utf-8"
            )
            payload = {"status": "passed", "patch": evidence.model_dump(mode="json")}
    except (OSError, ValueError, RepairWorktreeError) as exc:
        print(f"repair worktree error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
