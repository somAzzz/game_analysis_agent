"""Deterministic, authoring-only gateway for creating exact Replay fixtures."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

from .persona_gateway import (
    PersonaCallMetadata,
    PersonaDecisionRequest,
    PersonaDecisionResult,
    PersonaEventChoice,
    PersonaEventChoiceRequest,
    PersonaEventChoiceResult,
    PersonaParseStatus,
    PersonaProvider,
    PersonaProviderMode,
    PersonaResultStatus,
)
from .recorded_persona_gateway import FIXTURE_SCHEMA, MANIFEST_SCHEMA
from .schemas import PlayerDecision

PREFERENCES = {
    "newbie": ("food", "recovery", "study", "admin"),
    "study": ("study", "admin", "food", "recovery"),
    "money": ("work", "food", "study", "recovery"),
    "social": ("social", "food", "recovery", "study"),
    "visa": ("admin", "study", "recovery", "food"),
    "slacker": ("recovery", "escape", "social", "food"),
}


class FixtureAuthoringGateway:
    """Record deterministic legal choices; never use as a campaign provider."""

    provider = PersonaProvider.REPLAY
    mode = PersonaProviderMode.REPLAY
    model = "fixture-authoring-policy-v1"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, dict] = {}

    def decide(self, request: PersonaDecisionRequest) -> PersonaDecisionResult:
        actions = _select_actions(request)
        decision = PlayerDecision(
            week=request.context.state.week,
            persona=request.context.persona,
            strategic_goal=f"exercise {request.context.persona} priorities",
            actions=actions,
            risk_awareness=[item.id for item in request.context.top_risks[:3]],
            expected_tradeoff="deterministic fixture authoring choice",
            confidence=1.0,
        )
        entry = {
            "entry_id": request.request_id,
            "kind": "decision",
            "fingerprint": request.fingerprint(),
            "persona": request.context.persona,
            "seed": request.context.seed,
            "week": request.context.state.week,
            "state_hash": request.state_hash,
            "decision": decision.model_dump(mode="json"),
        }
        self._record(entry)
        return PersonaDecisionResult(
            status=PersonaResultStatus.COMPLETED,
            request_fingerprint=request.fingerprint(),
            decision=decision,
            metadata=self._metadata(request.request_id),
        )

    def choose_event(
        self, request: PersonaEventChoiceRequest
    ) -> PersonaEventChoiceResult:
        choices = request.context.event_choices
        if not choices:
            raise ValueError("fixture authoring event request has no choices")
        payload = (
            f"{request.context.persona}:{request.context.seed}:"
            f"{request.context.state.week}:{request.context.current_event_id}"
        ).encode()
        index = int(hashlib.sha256(payload).hexdigest()[:8], 16) % len(choices)
        choice = PersonaEventChoice(
            week=request.context.state.week,
            persona=request.context.persona,
            event_id=request.context.current_event_id,
            event_choice_id=choices[index].choice_id,
        )
        entry = {
            "entry_id": request.request_id,
            "kind": "event_choice",
            "fingerprint": request.fingerprint(),
            "persona": request.context.persona,
            "seed": request.context.seed,
            "week": request.context.state.week,
            "state_hash": request.state_hash,
            "choice": choice.model_dump(mode="json"),
        }
        self._record(entry)
        return PersonaEventChoiceResult(
            status=PersonaResultStatus.COMPLETED,
            request_fingerprint=request.fingerprint(),
            choice=choice,
            metadata=self._metadata(request.request_id),
        )

    def fixture_payload(self, *, fixture_id: str) -> dict:
        with self._lock:
            entries = sorted(
                self._entries.values(),
                key=lambda item: (
                    item["persona"],
                    item["seed"],
                    item["week"],
                    item["kind"],
                    item["entry_id"],
                ),
            )
        return {
            "schema_version": FIXTURE_SCHEMA,
            "fixture_id": fixture_id,
            "authoring_policy": self.model,
            "entries": entries,
        }

    def write(
        self,
        *,
        project_root: str | Path,
        fixture_path: str | Path,
        manifest_path: str | Path,
        fixture_id: str,
    ) -> tuple[Path, Path, str]:
        root = Path(project_root).resolve()
        fixture = Path(fixture_path)
        manifest = Path(manifest_path)
        if not fixture.is_absolute():
            fixture = root / fixture
        if not manifest.is_absolute():
            manifest = root / manifest
        fixture.parent.mkdir(parents=True, exist_ok=True)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text(
            json.dumps(
                self.fixture_payload(fixture_id=fixture_id),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
        try:
            relative = fixture.relative_to(root).as_posix()
        except ValueError as exc:
            raise ValueError("Replay fixture must be repository-relative") from exc
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": MANIFEST_SCHEMA,
                    "fixture": relative,
                    "sha256": digest,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return fixture, manifest, digest

    def _record(self, entry: dict) -> None:
        fingerprint = str(entry["fingerprint"])
        with self._lock:
            existing = self._entries.get(fingerprint)
            if existing is not None and existing != entry:
                raise ValueError(f"conflicting fixture entry: {fingerprint}")
            self._entries[fingerprint] = entry

    def _metadata(self, request_id: str) -> PersonaCallMetadata:
        return PersonaCallMetadata(
            provider=self.provider,
            mode=self.mode,
            model=self.model,
            response_id=request_id,
            parse_status=PersonaParseStatus.PARSED,
        )


def _select_actions(request: PersonaDecisionRequest) -> list[str]:
    context = request.context
    actions = context.available_actions
    if not actions:
        raise ValueError("fixture authoring context has no legal actions")
    by_id = {item.id: item for item in actions}
    selected = []
    suggested = [
        action_id
        for risk in context.top_risks
        for action_id in risk.suggested_action_ids
        if action_id in by_id
    ]
    for action_id in suggested:
        if action_id not in selected:
            selected.append(action_id)
        if len(selected) >= context.max_action_slots:
            return selected
    for preference in PREFERENCES.get(context.persona, PREFERENCES["newbie"]):
        for action in actions:
            signals = {action.id, action.type, *action.tags, *action.risk_tags}
            if preference in signals and action.id not in selected:
                selected.append(action.id)
                break
        if len(selected) >= context.max_action_slots:
            return selected
    for action in actions:
        if action.id not in selected:
            selected.append(action.id)
        if len(selected) >= context.max_action_slots:
            break
    return selected


__all__ = ["FixtureAuthoringGateway", "PREFERENCES"]
