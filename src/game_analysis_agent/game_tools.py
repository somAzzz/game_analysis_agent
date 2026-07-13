"""OpenAI tool schemas + Godot subprocess wrappers for the
``interactive_player`` agent.

The agent drives a single playthrough via these tools. Each tool maps
to a thin Python wrapper that shells out to the headless Godot runner
(``scripts/tools/RunInteractiveProbe.gd``) and waits for its result.

Tool loop wiring lives in :mod:`game_analysis_agent.tool_loop`. This module
only declares the schemas + handlers + lifecycle (one ``InteractiveProbe``
per playthrough).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from game_analysis_agent.contracts import (
    ContractKind,
    ContractValidationError,
    validate_contract,
)
from game_analysis_agent.schemas import Anomaly
from game_analysis_agent.settings import Settings, get_settings


@dataclass
class InteractiveProbe:
    """Persistent handle to one in-flight playthrough.

    The Godot ``RunInteractiveProbe.gd`` is a *single-shot* runner: it
    reads a complete ``week_plan`` from a JSON file and dumps the trace.
    Real interactive play (LLM-driven) therefore accumulates a ``week_plan``
    in memory as the model decides, then flushes to Godot for each
    ``step()`` and reads back the new state.
    """

    settings: Settings
    plan: list[dict[str, Any]] = field(default_factory=list)
    seed: int = 42
    difficulty: str = "normal"
    scenario: str = "default_first_semester"
    current_week: int = 0
    state: dict[str, Any] | None = None
    last_event_id: str = ""
    last_event_choices: list[dict[str, Any]] = field(default_factory=list)
    available_actions: list[dict[str, Any]] = field(default_factory=list)
    risk_guidance: dict[str, Any] | None = None
    finished: bool = False
    final_ending: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    # -- tool implementations ---------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Return the latest known state (or an empty dict before step 1)."""
        if self.state is None:
            self._refresh_snapshot()
        return {
            "week": self.current_week,
            "state": self.state or {},
            "finished": self.finished,
            "last_event_id": self.last_event_id,
            "risk_guidance": self.risk_guidance,
        }

    def list_available_actions(self) -> dict[str, Any]:
        """Return currently legal actions for the active playthrough state."""
        if self.state is None or not self.available_actions:
            self._refresh_snapshot()
        return {"actions": self.available_actions}

    def inspect_action(self, action_id: str) -> dict[str, Any]:
        catalog = self.list_available_actions()
        for action in catalog.get("actions", []) or []:
            if isinstance(action, dict) and action.get("id") == action_id:
                return action
        return {"error": f"action_id not found: {action_id}"}

    def inspect_event(self, event_id: str) -> dict[str, Any]:
        graph_path = self.settings.game_project_path / "reports" / "event_graph.json"
        if not graph_path.exists():
            return _maybe_run_export(self.settings)
        try:
            payload = json.loads(graph_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"error": "event_graph.json is not valid JSON"}
        for event in payload.get("events", []):
            if event.get("id") == event_id:
                return event
        return {"error": f"event_id not found: {event_id}"}

    def step(
        self,
        actions: list[str],
        event_choice_id: str = "",
    ) -> dict[str, Any]:
        """Submit a one-step plan to Godot and merge the result back in."""
        if self.finished:
            return {"error": "playthrough is already finished"}
        if not actions:
            return {"error": "actions list must not be empty"}
        self.plan.append(
            {
                "week": self.current_week + 1,
                "action_ids": list(actions),
                "event_choice_id": event_choice_id,
            }
        )
        result = _run_one_step(
            self.settings,
            self.plan,
            seed=self.seed,
            difficulty=self.difficulty,
            scenario=self.scenario,
        )
        self.current_week += 1
        self.state = result.get("current_state") or result.get("after_state") or self.state or {}
        self.last_event_id = result.get("triggered_event_id", "")
        self.last_event_choices = result.get("event_choices", []) or []
        self.available_actions = result.get("next_available_actions", []) or []
        guidance = result.get("risk_guidance")
        self.risk_guidance = guidance if isinstance(guidance, dict) else None
        self.history.append(
            {
                "week": self.current_week,
                "actions": list(actions),
                "event_choice_id": event_choice_id,
                "triggered_event_id": self.last_event_id,
                "after_state": self.state,
            }
        )
        if result.get("finished"):
            self.finished = True
            self.final_ending = result.get("final_ending_id", "unknown")
        return {
            "week": self.current_week,
            "state": self.state,
            "triggered_event_id": self.last_event_id,
            "event_choices": self.last_event_choices,
            "risk_guidance": self.risk_guidance,
            "finished": self.finished,
        }

    def preview_step(self, actions: list[str]) -> dict[str, Any]:
        """Preview this week's event choices without committing the week."""
        if self.finished:
            return {"error": "playthrough is already finished"}
        if not actions:
            return {"error": "actions list must not be empty"}
        preview_plan = [
            *self.plan,
            {
                "week": self.current_week + 1,
                "action_ids": list(actions),
                "event_choice_id": "",
                "defer_event_choice": True,
            },
        ]
        return _run_one_step(
            self.settings,
            preview_plan,
            seed=self.seed,
            difficulty=self.difficulty,
            scenario=self.scenario,
        )

    def _refresh_snapshot(self) -> None:
        try:
            result = _run_one_step(
                self.settings,
                self.plan,
                seed=self.seed,
                difficulty=self.difficulty,
                scenario=self.scenario,
            )
        except FileNotFoundError:
            return
        self.state = result.get("current_state") or result.get("after_state") or self.state or {}
        self.available_actions = (
            result.get("next_available_actions") or result.get("available_actions") or []
        )
        self.last_event_id = result.get("triggered_event_id", self.last_event_id)
        self.last_event_choices = result.get("event_choices", []) or self.last_event_choices
        guidance = result.get("risk_guidance")
        self.risk_guidance = guidance if isinstance(guidance, dict) else None

    def finish(self) -> dict[str, Any]:
        if self.plan:
            final = _run_one_step(
                self.settings,
                self.plan,
                force_finish=True,
                seed=self.seed,
                difficulty=self.difficulty,
                scenario=self.scenario,
            )
            self.state = final.get("final_state") or final.get("after_state") or self.state or {}
            self.final_ending = final.get("final_ending_id") or self.final_ending or "unknown"
            guidance = final.get("risk_guidance")
            self.risk_guidance = guidance if isinstance(guidance, dict) else None
        self.finished = True
        return {
            "finished": True,
            "final_state": self.state,
            "final_ending": self.final_ending,
            "risk_guidance": self.risk_guidance,
        }

    # -- diagnostics -------------------------------------------------------

    def detect_anomalies(self) -> list[Anomaly]:
        """Run the deterministic anomaly detector on this run's history."""
        from game_analysis_agent.anomaly_detector import detect_anomalies

        synthetic_run = {
            "run_id": 0,
            "policy": "interactive_player",
            "max_weeks": max((step["week"] for step in self.history), default=self.current_week),
            "final_ending_id": self.final_ending or "",
            "weekly_log": [
                {
                    "week": step["week"],
                    "selected_action_ids": step["actions"],
                    "triggered_event_id": step["triggered_event_id"],
                    "after_state": step["after_state"],
                }
                for step in self.history
            ],
        }
        return detect_anomalies([synthetic_run])


# -----------------------------------------------------------------------
# Tool schemas
# -----------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_state",
            "description": "Return the latest public game-state snapshot for the active playthrough.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_available_actions",
            "description": "List every action id exposed by the game, plus cost/effect metadata.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_event",
            "description": "Return the definition (title / body / choices / trigger / set_flag) of one event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "Event id, e.g. 'first_lecture'.",
                    }
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_action",
            "description": "Return the full cost/effect/tag metadata for one action id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_id": {
                        "type": "string",
                        "description": "Action id, e.g. 'library_day'.",
                    }
                },
                "required": ["action_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "step",
            "description": (
                "Advance the playthrough by one week. Submit the chosen action ids and "
                "(optionally) the id of the event choice if one triggered. Returns the new state."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "actions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Action ids to schedule this week (max 4).",
                    },
                    "event_choice_id": {
                        "type": "string",
                        "description": "Choice id to submit if an event triggers this week; pass '' to default.",
                    },
                },
                "required": ["actions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Close out the playthrough and ask the simulator for the final ending.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def build_tool_map(probe: InteractiveProbe) -> dict[str, Callable[..., Any]]:
    return {
        "get_state": probe.get_state,
        "list_available_actions": probe.list_available_actions,
        "inspect_event": probe.inspect_event,
        "inspect_action": probe.inspect_action,
        "step": probe.step,
        "finish": probe.finish,
    }


# -----------------------------------------------------------------------
# Godot subprocess glue
# -----------------------------------------------------------------------


def build_probe(settings: Settings | None = None) -> InteractiveProbe:
    return InteractiveProbe(settings=settings or get_settings(), plan=[])


def _maybe_run_export(settings: Settings) -> dict[str, Any]:
    """Run ExportEventGraph.gd and re-read."""
    out = _run_export(settings)
    if not out.exists():
        return {"error": "ExportEventGraph.gd did not produce event_graph.json"}
    return {"status": "exported", "path": str(out)}


def _run_export(settings: Settings) -> Path:
    out_path = settings.game_project_path / "reports" / "event_graph.json"
    plan_path = settings.game_project_path / "reports" / "_plan.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps({"command": "export", "weeks": 0}, ensure_ascii=False),
        encoding="utf-8",
    )
    _invoke_godot(
        settings,
        script="res://scripts/tools/ExportEventGraph.gd",
        extra_args=[f"--plan={plan_path}", f"--out={out_path}"],
    )
    return out_path


def _run_one_step(
    settings: Settings,
    plan: list[dict[str, Any]],
    force_finish: bool = False,
    *,
    seed: int = 42,
    difficulty: str = "normal",
    scenario: str = "default_first_semester",
) -> dict[str, Any]:
    plan_path = settings.game_project_path / "reports" / f"_plan_{uuid.uuid4().hex[:8]}.json"
    out_path = settings.game_project_path / "reports" / f"_trace_{uuid.uuid4().hex[:8]}.json"
    plan_payload = {
        "command": "step",
        "seed": seed,
        "difficulty": difficulty,
        "scenario": scenario,
        "weeks": max((step["week"] for step in plan), default=0),
        "plan": plan,
        "force_finish": force_finish,
    }
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan_payload, ensure_ascii=False), encoding="utf-8")
    try:
        completed = _invoke_godot(
            settings,
            script="res://scripts/tools/RunInteractiveProbe.gd",
            extra_args=[f"--plan={plan_path}", f"--out={out_path}"],
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "RunInteractiveProbe failed: "
                + (completed.stderr[-2000:] or completed.stdout[-2000:])
            )
        if not out_path.exists():
            raise RuntimeError("RunInteractiveProbe did not produce a trace")
        try:
            payload = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"RunInteractiveProbe produced invalid JSON: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("RunInteractiveProbe trace root must be an object")
        try:
            validate_contract(payload, kind=ContractKind.INTERACTIVE_PROBE)
        except ContractValidationError as exc:
            raise RuntimeError(f"RunInteractiveProbe contract failed: {exc}") from exc
        return payload
    finally:
        plan_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)


def _invoke_godot(
    settings: Settings, *, script: str, extra_args: list[str]
) -> subprocess.CompletedProcess[str]:
    godot_bin = settings.godot_bin
    if shutil.which(godot_bin) is None:
        # Many systems expose ``godot`` instead of ``godot4``. Try that.
        fallback = "godot" if godot_bin == "godot4" else None
        if fallback and shutil.which(fallback):
            godot_bin = fallback
    cmd = [
        godot_bin,
        "--headless",
        "--path",
        str(settings.game_project_path),
        "-s",
        script,
        *extra_args,
    ]
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )


__all__ = [
    "InteractiveProbe",
    "TOOL_DEFINITIONS",
    "Anomaly",
    "build_probe",
    "build_tool_map",
]
