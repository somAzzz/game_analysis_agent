"""Tests for ``tools.build_dashboard``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from build_dashboard import (
    _aggregate_balance_issue,
    _choice_index_from_id,
    _compute_graph_layout,
    _decision_graph_payload,
    _discover_issues,
    _lane_for_event,
    _trigger_week,
    _wedge_path,
    _write_diagnostics_json,
    render_decision_graph_page,
    render_front_page,
    render_issue,
    render_markdown,
)


def test_render_markdown_handles_headings_and_paragraphs() -> None:
    md = "# Hello\n\nA *paragraph* with **bold** and `code`."
    out = render_markdown(md)
    assert "<h1 class='md-h1'>Hello</h1>" in out
    assert "<strong>bold</strong>" in out
    assert "<em>paragraph</em>" in out
    assert "<code>code</code>" in out


def test_render_markdown_handles_lists() -> None:
    md = "- one\n- two\n- three"
    out = render_markdown(md)
    assert "<ul class='md-list'>" in out
    assert "<li>one</li>" in out
    assert "<li>two</li>" in out


def test_render_markdown_handles_blockquote() -> None:
    md = "> A pull quote"
    out = render_markdown(md)
    assert "<blockquote class='md-quote'>A pull quote</blockquote>" in out


def test_render_markdown_handles_code_fence() -> None:
    md = "```python\nprint('hi')\n```"
    out = render_markdown(md)
    assert "<pre class='md-code'>" in out
    assert "data-lang='python'" in out


def test_render_markdown_handles_table() -> None:
    md = "| a | b |\n| --- | --- |\n| 1 | 2 |"
    out = render_markdown(md)
    assert "<table class='md-table'>" in out
    assert "<th>a</th>" in out
    assert "<td>1</td>" in out


def test_render_markdown_escapes_html() -> None:
    md = "<script>alert('xss')</script>"
    out = render_markdown(md)
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_render_front_page_emits_masthead_and_kpis() -> None:
    issues = []
    html = render_front_page(issues)
    assert "The Analytical" in html
    assert "<h1" in html
    assert "Fraunces" in html  # font name in @import
    assert "kpi-strip" in html


def test_render_issue_emits_cover_and_marginalia() -> None:
    issues = _discover_issues(Path(__file__).resolve().parents[1] / "reports")
    if not issues:
        return
    html = render_issue(issues[0])
    assert "issue-meta" in html
    assert "marginalia" in html
    assert "<!doctype html>" in html


def test_aggregate_balance_issue_reads_summary(tmp_path) -> None:
    """Ensure the aggregator produces a sensible Issue even with minimal data."""
    (tmp_path / "summary.json").write_text(
        '{"total_runs": 5, "policies": {"balanced": 5}, "top_events": {"arrival": 5}}',
        encoding="utf-8",
    )
    (tmp_path / "ending_distribution.csv").write_text(
        "policy,ending_id,count,rate\nbalanced,academic_success,5,1.0\n",
        encoding="utf-8",
    )
    (tmp_path / "weekly_stats.csv").write_text(
        "policy,week,metric,mean,median,p10,p90,min,max\n"
        "balanced,1,stress,20,20,10,30,0,40\n"
        "balanced,2,stress,40,40,20,60,10,70\n",
        encoding="utf-8",
    )
    issue = _aggregate_balance_issue(tmp_path, slug=f"test/{tmp_path.name}")
    assert issue is not None
    assert issue.total_runs == 5
    assert issue.endings[0]["ending_id"] == "academic_success"
    assert any(p.metric == "stress" for p in issue.weekly_series)


# ---------------------------------------------------------------------------
# Decision-graph view
# ---------------------------------------------------------------------------


def test_compute_graph_layout_separates_lanes() -> None:
    events = [
        {"id": "e1", "event_type": "fixed", "trigger": {"week": 3}, "source_order": 0},
        {"id": "e2", "event_type": "conditional", "trigger": {}, "source_order": 5},
        {"id": "e3", "event_type": "random", "trigger": {}, "source_order": 9},
    ]
    layout = _compute_graph_layout(events, max_week=10)
    assert "e1" in layout.positions
    assert "e2" in layout.positions
    assert "e3" in layout.positions
    ys = {k: v[1] for k, v in layout.positions.items()}
    assert ys["e1"] < ys["e2"] < ys["e3"]


def test_wedge_path_returns_svg_d() -> None:
    path = _wedge_path(cx=100, cy=100, r=10, idx=0, total=4)
    assert path.startswith("M 100.00 100.00")
    assert " A 10.00" in path
    assert path.endswith("Z")


def test_wedge_path_handles_zero_total() -> None:
    assert _wedge_path(0, 0, 10, 0, 0) == ""


def test_decision_graph_payload_extracts_choices() -> None:
    events = [
        {
            "id": "first_lecture",
            "title": "First lecture",
            "event_type": "fixed",
            "trigger": {"week": 1},
            "choices": [
                {"text": "ask question", "success_effects": {"language": 3}},
                {"text": "stay silent", "success_effects": {"stress": -1}},
            ],
        },
        {
            "id": "visa_notice",
            "title": "Visa notice",
            "event_type": "conditional",
            "trigger": {"week": 5},
            "choices": [{"text": "apply"}, {"text": "ignore"}],
        },
    ]
    run = {
        "run_id": 0,
        "policy": "balanced",
        "scenario": "default_first_semester",
        "seed": 42,
        "max_weeks": 20,
        "final_ending_id": "academic_success",
        "weekly_log": [
            {
                "week": 1,
                "triggered_event_id": "first_lecture",
                "event_choice_id": "first_lecture.choice_01_ask_question",
                "selected_action_ids": ["study_library"],
                "after_state": {"money": 1000},
            },
            {
                "week": 5,
                "triggered_event_id": "visa_notice",
                "event_choice_id": "visa_notice.choice_02_ignore",
                "selected_action_ids": ["rest_at_home"],
                "after_state": {"visa_progress": 60},
            },
        ],
    }
    payload = _decision_graph_payload({"events": events}, run)
    assert len(payload["events"]) == 2
    first = payload["events"][0]
    assert first["event_id"] == "first_lecture"
    assert first["choice_index"] == 0
    assert first["choice_text"] == "ask question"
    assert first["choice_effects"] == {"language": 3}
    second = payload["events"][1]
    assert second["choice_index"] == 1
    assert second["choice_text"] == "ignore"


def test_render_decision_graph_page_emits_key_sections(tmp_path) -> None:
    event_graph = {
        "events": [
            {
                "id": "first_lecture",
                "title": "First lecture",
                "body": "Welcome.",
                "event_type": "fixed",
                "trigger": {"week": 1},
                "choices": [
                    {"text": "ask question", "success_effects": {"language": 3}},
                ],
            }
        ]
    }
    run = {
        "run_id": 0,
        "policy": "balanced",
        "scenario": "default_first_semester",
        "seed": 42,
        "max_weeks": 5,
        "final_ending_id": "academic_success",
        "weekly_log": [
            {
                "week": 1,
                "triggered_event_id": "first_lecture",
                "event_choice_id": "first_lecture.choice_01_ask_question",
                "selected_action_ids": ["study_library"],
                "after_state": {"money": 1000},
            }
        ],
    }
    page = render_decision_graph_page(
        report_dir=tmp_path, run=run, event_graph=event_graph
    )
    assert "<svg" in page
    assert "The decision <em>graph</em>" in page
    assert "choice-panel" in page
    assert "setCurrent" in page
    assert "first_lecture" in page
    # JSON payload is embedded for the JS interactivity
    assert 'type="application/json"' in page


# ---------------------------------------------------------------------------
# Adaptive behaviour — the generator must re-layout itself when the upstream
# event tree evolves (new event_type, renamed trigger key, renamed choice_id
# convention, missing fields, etc).
# ---------------------------------------------------------------------------


def test_layout_adapts_to_new_event_types() -> None:
    events = [
        {"id": "f", "event_type": "fixed", "trigger": {"week": 1}, "choices": []},
        {"id": "c", "event_type": "conditional", "choices": []},
        {"id": "r1", "event_type": "random", "choices": []},
        {"id": "r2", "event_type": "random", "choices": []},
        # Brand new lane the schema author just added:
        {"id": "m", "event_type": "meta", "choices": []},
        {"id": "sc", "event_type": "scripted", "choices": []},
    ]
    layout = _compute_graph_layout(events, max_week=20)
    # All five lanes appear — the new types get their own lanes automatically.
    assert set(layout.lane_order) == {"fixed", "conditional", "random", "meta", "scripted"}
    # New lanes have their own y coordinates, not collided with old ones.
    assert layout.lane_y["meta"] != layout.lane_y["fixed"]
    assert layout.lane_y["scripted"] != layout.lane_y["conditional"]
    # Every event has a position — none silently dropped.
    assert set(layout.positions.keys()) == {"f", "c", "r1", "r2", "m", "sc"}


def test_layout_orders_lanes_by_frequency() -> None:
    """More populous lanes render first (top of canvas) so the eye lands there."""
    events = (
        [{"id": f"r{i}", "event_type": "random", "choices": []} for i in range(8)]
        + [{"id": f"f{i}", "event_type": "fixed", "choices": []} for i in range(3)]
        + [{"id": "c", "event_type": "conditional", "choices": []}]
    )
    layout = _compute_graph_layout(events, max_week=20)
    # `random` has 8 events, `fixed` has 3, `conditional` has 1.
    assert layout.lane_order[0] == "random"
    assert layout.lane_order[-1] == "conditional"


def test_layout_height_scales_with_lane_count() -> None:
    one_lane = _compute_graph_layout(
        [{"id": "a", "event_type": "fixed", "choices": []}], max_week=10
    )
    six_lanes = _compute_graph_layout(
        [
            {"id": f"x{i}", "event_type": name, "choices": []}
            for i, name in enumerate(["a", "b", "c", "d", "e", "f"])
        ],
        max_week=10,
    )
    assert six_lanes.height > one_lane.height


def test_trigger_week_accepts_alternate_field_names() -> None:
    assert _trigger_week({"week": 5}) == 5.0
    assert _trigger_week({"min_week": 3}) == 3.0
    assert _trigger_week({"start_week": 7}) == 7.0
    assert _trigger_week({"at_week": 1}) == 1.0
    assert _trigger_week({"fire_week": 9}) == 9.0
    assert _trigger_week({"weeks": [4, 8]}) == 4.0
    assert _trigger_week({}) is None
    assert _trigger_week(None) is None
    # Negative weeks (countdowns from end) → None, so source_order fallback kicks in.
    assert _trigger_week({"week": -3}) is None


def test_choice_index_from_id_accepts_alternate_formats() -> None:
    # Legacy convention
    assert _choice_index_from_id("first_lecture.choice_01_ask_question", 4) == 0
    assert _choice_index_from_id("first_lecture.choice_02", 4) == 1
    # Slash / colon / underscore variants
    assert _choice_index_from_id("first_lecture/c2", 4) == 1
    assert _choice_index_from_id("first_lecture:choice3", 4) == 2
    assert _choice_index_from_id("first_lecture:4", 4) == 3
    assert _choice_index_from_id("first_lecture_2", 4) == 1
    # No match → -1 (no wedge rendered)
    assert _choice_index_from_id("totally-opaque-id", 4) == -1
    # Out of range → -1
    assert _choice_index_from_id("event.choice_99_x", 4) == -1
    # Empty / None safe
    assert _choice_index_from_id("", 4) == -1
    assert _choice_index_from_id("anything", 0) == -1


def test_lane_for_event_tolerates_alternate_field_names() -> None:
    assert _lane_for_event({"event_type": "fixed"}) == "fixed"
    assert _lane_for_event({"type": "scripted"}) == "scripted"
    assert _lane_for_event({"kind": "triggered"}) == "triggered"
    # Empty / missing falls into "uncategorised" rather than crashing or
    # silently merging into another lane.
    assert _lane_for_event({"id": "x"}) == "uncategorised"
    assert _lane_for_event({"event_type": ""}) == "uncategorised"
    # Whitespace gets normalised
    assert _lane_for_event({"event_type": "  Meta  "}) == "meta"


def test_payload_handles_alternative_trigger_field() -> None:
    """A future schema using ``fire_week`` instead of ``week`` should still work."""
    events = [
        {
            "id": "future_event",
            "title": "Future event",
            "event_type": "fixed",
            "trigger": {"fire_week": 5},  # alt field name
            "choices": [{"text": "a"}, {"text": "b"}],
        }
    ]
    run = {
        "run_id": 0,
        "policy": "balanced",
        "max_weeks": 20,
        "weekly_log": [
            {
                "week": 5,
                "triggered_event_id": "future_event",
                "event_choice_id": "future_event/c1",  # alt choice_id format
                "selected_action_ids": [],
                "after_state": {},
            }
        ],
    }
    payload = _decision_graph_payload({"events": events}, run)
    assert len(payload["events"]) == 1
    ev = payload["events"][0]
    assert ev["choice_index"] == 0  # /c1 → index 0
    # Diagnostics should NOT contain "could not parse choice_index" warnings.
    assert not any("Could not parse" in d for d in payload["diagnostics"])


def test_payload_adapts_to_unknown_event_type() -> None:
    """An event with an unknown type still gets placed + rendered."""
    events = [
        {
            "id": "exotic",
            "title": "Exotic",
            "event_type": "quantum_entangled",
            "trigger": {"phase": 3},
            "choices": [{"text": "yes"}, {"text": "no"}],
        }
    ]
    run = {
        "run_id": 0,
        "policy": "study",
        "max_weeks": 20,
        "weekly_log": [
            {
                "week": 7,
                "triggered_event_id": "exotic",
                "event_choice_id": "exotic.choice_01_yes",
                "selected_action_ids": [],
                "after_state": {},
            }
        ],
    }
    payload = _decision_graph_payload({"events": events}, run)
    assert "quantum_entangled" in payload["lane_order"]
    assert payload["events"][0]["event_type"] == "quantum_entangled"
    assert payload["events"][0]["choice_index"] == 0


def test_payload_records_diagnostics_for_missing_event() -> None:
    """If a triggered event is not in event_graph.json, the diagnostic log records it."""
    events = [
        {"id": "known", "event_type": "fixed", "trigger": {"week": 1}, "choices": [{"text": "a"}]}
    ]
    run = {
        "run_id": 0,
        "policy": "balanced",
        "max_weeks": 5,
        "weekly_log": [
            {
                "week": 1,
                "triggered_event_id": "known",
                "event_choice_id": "known.choice_01_a",
                "selected_action_ids": [],
                "after_state": {},
            },
            {
                "week": 2,
                "triggered_event_id": "ghost_event",
                "event_choice_id": "ghost.choice_01_x",
                "selected_action_ids": [],
                "after_state": {},
            },
        ],
    }
    payload = _decision_graph_payload({"events": events}, run)
    assert len(payload["events"]) == 1
    assert any("ghost_event" in d for d in payload["diagnostics"])


def test_payload_handles_missing_choice_text() -> None:
    """A choice with no 'text' field should not crash — fall back gracefully."""
    events = [
        {
            "id": "e",
            "event_type": "fixed",
            "trigger": {"week": 1},
            "choices": [
                {"success_effects": {"money": 100}},  # no "text"
            ],
        }
    ]
    run = {
        "run_id": 0,
        "policy": "balanced",
        "max_weeks": 5,
        "weekly_log": [
            {
                "week": 1,
                "triggered_event_id": "e",
                "event_choice_id": "e.choice_01",
                "selected_action_ids": [],
                "after_state": {},
            }
        ],
    }
    payload = _decision_graph_payload({"events": events}, run)
    assert payload["events"][0]["choice_text"] == ""
    assert payload["events"][0]["choice_effects"] == {"money": 100.0}


def test_payload_handles_explicit_choice_index_field() -> None:
    """If a future schema emits a direct ``choice_index`` field, prefer it."""
    events = [
        {
            "id": "e",
            "event_type": "fixed",
            "trigger": {"week": 1},
            "choices": [{"text": "a"}, {"text": "b"}, {"text": "c"}],
        }
    ]
    run = {
        "run_id": 0,
        "policy": "balanced",
        "max_weeks": 5,
        "weekly_log": [
            {
                "week": 1,
                "triggered_event_id": "e",
                # No event_choice_id, but explicit choice_index → 2 (3rd choice)
                "choice_index": 2,
                "selected_action_ids": [],
                "after_state": {},
            }
        ],
    }
    payload = _decision_graph_payload({"events": events}, run)
    assert payload["events"][0]["choice_index"] == 2


def test_diagnostics_json_written(tmp_path) -> None:
    """The CLI emits a `_diagnostics.json` next to the rendered page."""
    raw = tmp_path / "raw.jsonl"
    raw.write_text(
        json.dumps(
            {
                "run_id": 0,
                "policy": "balanced",
                "max_weeks": 5,
                "weekly_log": [
                    {
                        "week": 1,
                        "triggered_event_id": "x",
                        "event_choice_id": "x.choice_01",
                        "selected_action_ids": [],
                        "after_state": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    graph = tmp_path / "graph.json"
    graph.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "id": "x",
                        "title": "X",
                        "event_type": "fixed",
                        "trigger": {"week": 1},
                        "choices": [{"text": "a"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    event_graph = json.loads(graph.read_text())
    runs = [json.loads(line) for line in raw.read_text().splitlines() if line.strip()]
    payload = _decision_graph_payload(event_graph, runs[0])
    _write_diagnostics_json(
        tmp_path,
        event_graph=event_graph,
        payload=payload,
        raw_runs_path=raw,
        event_graph_path=graph,
    )
    diag = tmp_path / "_diagnostics.json"
    assert diag.exists()
    parsed = json.loads(diag.read_text())
    assert "event_types" in parsed["event_graph_summary"]
    assert "lane_order" in parsed["event_graph_summary"]
    assert "diagnostics_notes" in parsed["adaptations"]


def test_layout_max_week_widens_to_observed() -> None:
    """If a weekly_log goes past max_weeks, the layout should auto-widen."""
    events = [
        {"id": "e", "event_type": "fixed", "trigger": {"week": 30}, "choices": []}
    ]
    run = {
        "run_id": 0,
        "policy": "balanced",
        "max_weeks": 20,
        "weekly_log": [
            {
                "week": 35,  # past declared max_weeks
                "triggered_event_id": "e",
                "event_choice_id": "e.choice_01",
                "selected_action_ids": [],
                "after_state": {},
            }
        ],
    }
    payload = _decision_graph_payload({"events": events}, run)
    # max_week should have grown to fit the observation.
    assert payload["max_week"] >= 35