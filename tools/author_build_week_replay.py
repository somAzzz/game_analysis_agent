#!/usr/bin/env python3
"""Author the full exact Replay fixture from the pinned real Godot game."""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.agents.interactive_player import InteractivePlayerAgent  # noqa: E402
from game_analysis_agent.campaign_contract import (  # noqa: E402
    CampaignRequest,
    build_campaign_cells,
)
from game_analysis_agent.game_tools import build_probe  # noqa: E402
from game_analysis_agent.persona_fixture_authoring import (  # noqa: E402
    FixtureAuthoringGateway,
)
from game_analysis_agent.recorded_persona_gateway import (  # noqa: E402
    RecordedPersonaGateway,
)
from game_analysis_agent.settings import Settings  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "config/build_week_2026_campaign.json"
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=ROOT / "fixtures/persona_replay/build_week_2026_full_v1.json",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "config/build_week_2026_full_replay.json",
    )
    parser.add_argument(
        "--authoring-root",
        type=Path,
        default=ROOT / "reports/build-week-2026/replay-authoring",
    )
    parser.add_argument("--replace", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if (args.fixture.exists() or args.manifest.exists()) and not args.replace:
        print("Replay fixture/manifest exists; pass --replace", file=sys.stderr)
        return 2
    request = CampaignRequest.model_validate_json(args.config.read_text(encoding="utf-8"))
    settings = Settings()
    if not (settings.game_project_path / "project.godot").is_file():
        print("GAME_PROJECT_PATH does not contain project.godot", file=sys.stderr)
        return 2
    author = FixtureAuthoringGateway()
    failures = []

    def run_cell(cell) -> tuple[str, int]:  # noqa: ANN001
        output = args.authoring_root / cell.cell_id
        agent = InteractivePlayerAgent(
            llm=None,
            persona_gateway=author,
            prompts_root=ROOT / "prompts",
            settings=settings,
            max_weeks=cell.max_weeks,
            persona=cell.persona.value,
            difficulty=cell.difficulty,
            scenario=cell.scenario,
            seed=cell.seed,
        )
        result, _paths = agent.play_through(output, probe=build_probe(settings))
        return cell.cell_id, len(result.steps)

    cells = build_campaign_cells(request)
    with ThreadPoolExecutor(max_workers=request.concurrency) as pool:
        futures = {pool.submit(run_cell, cell): cell for cell in cells}
        for future in as_completed(futures):
            cell = futures[future]
            try:
                cell_id, weeks = future.result()
                print(f"authored {cell_id}: {weeks} weeks", flush=True)
            except Exception as exc:
                failures.append((cell.cell_id, exc.__class__.__name__, str(exc)[:300]))
                print(f"failed {cell.cell_id}: {exc.__class__.__name__}", file=sys.stderr)
    if failures:
        print(json.dumps({"failures": failures}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    fixture, manifest, digest = author.write(
        project_root=ROOT,
        fixture_path=args.fixture,
        manifest_path=args.manifest,
        fixture_id="build-week-2026-full-v1",
    )
    replay = RecordedPersonaGateway.from_manifest(manifest, project_root=ROOT)
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "fixture": fixture.relative_to(ROOT).as_posix(),
                "manifest": manifest.relative_to(ROOT).as_posix(),
                "sha256": digest,
                "entries": len(payload["entries"]),
                "provider": replay.provider.value,
                "mode": replay.mode.value,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
