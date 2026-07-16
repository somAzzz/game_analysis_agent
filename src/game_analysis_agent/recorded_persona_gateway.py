"""Exact, hash-pinned Replay implementation of PersonaDecisionGateway."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .persona_gateway import (
    PersonaCallMetadata,
    PersonaDecisionRequest,
    PersonaDecisionResult,
    PersonaErrorCategory,
    PersonaEventChoice,
    PersonaEventChoiceRequest,
    PersonaEventChoiceResult,
    PersonaParseStatus,
    PersonaProvider,
    PersonaProviderError,
    PersonaProviderMode,
    PersonaResultStatus,
    validate_event_choice,
    validate_player_decision,
)
from .schemas import PlayerDecision

FIXTURE_SCHEMA = "persona-replay-fixture-v1"
MANIFEST_SCHEMA = "persona-replay-manifest-v1"


class ReplayFixtureError(ValueError):
    """Raised before execution when pinned Replay data is corrupt or malformed."""


class RecordedPersonaGateway:
    """Consume only exact, single-use decisions from a verified fixture."""

    provider = PersonaProvider.REPLAY
    mode = PersonaProviderMode.REPLAY

    def __init__(self, fixture_path: str | Path, *, expected_sha256: str) -> None:
        path = Path(fixture_path)
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise ReplayFixtureError(f"Replay fixture unavailable: {path.name}") from exc
        actual = hashlib.sha256(content).hexdigest()
        if actual != expected_sha256:
            raise ReplayFixtureError(
                f"Replay fixture hash mismatch: expected {expected_sha256}, got {actual}"
            )
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ReplayFixtureError(f"Replay fixture is invalid JSON: {path.name}") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != FIXTURE_SCHEMA:
            raise ReplayFixtureError(f"Replay fixture schema must be {FIXTURE_SCHEMA!r}")
        entries = payload.get("entries")
        if not isinstance(entries, list):
            raise ReplayFixtureError("Replay fixture entries must be a list")
        self.fixture_id = str(payload.get("fixture_id") or path.stem)
        self._entries: dict[str, dict[str, Any]] = {}
        self._consumed: set[str] = set()
        for index, entry in enumerate(entries):
            normalized = self._validate_entry(entry, index=index)
            fingerprint = normalized["fingerprint"]
            if fingerprint in self._entries:
                raise ReplayFixtureError(f"duplicate Replay fingerprint: {fingerprint}")
            self._entries[fingerprint] = normalized

    @classmethod
    def from_manifest(
        cls, manifest_path: str | Path, *, project_root: str | Path
    ) -> RecordedPersonaGateway:
        manifest_file = Path(manifest_path)
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ReplayFixtureError(f"Replay manifest unavailable: {manifest_file.name}") from exc
        if not isinstance(manifest, dict) or manifest.get("schema_version") != MANIFEST_SCHEMA:
            raise ReplayFixtureError(f"Replay manifest schema must be {MANIFEST_SCHEMA!r}")
        fixture = manifest.get("fixture")
        digest = manifest.get("sha256")
        if not isinstance(fixture, str) or Path(fixture).is_absolute() or ".." in Path(fixture).parts:
            raise ReplayFixtureError("Replay manifest fixture path is unsafe")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ReplayFixtureError("Replay manifest sha256 is invalid")
        return cls(Path(project_root) / fixture, expected_sha256=digest)

    def decide(self, request: PersonaDecisionRequest) -> PersonaDecisionResult:
        fingerprint = request.fingerprint()
        entry, error = self._take(fingerprint, kind="decision", request=request)
        metadata = self._metadata(entry)
        if error is not None:
            return PersonaDecisionResult(
                status=PersonaResultStatus.FAILED,
                request_fingerprint=fingerprint,
                metadata=metadata,
                error=error,
            )
        try:
            decision = PlayerDecision.model_validate(entry["decision"])
        except (KeyError, ValidationError) as exc:
            return self._decision_failure(
                fingerprint,
                metadata,
                f"recorded decision is malformed: {exc.__class__.__name__}",
            )
        errors = validate_player_decision(decision, request.context)
        if errors:
            return self._decision_failure(fingerprint, metadata, "; ".join(errors))
        return PersonaDecisionResult(
            status=PersonaResultStatus.COMPLETED,
            request_fingerprint=fingerprint,
            decision=decision,
            metadata=metadata,
        )

    def choose_event(
        self, request: PersonaEventChoiceRequest
    ) -> PersonaEventChoiceResult:
        fingerprint = request.fingerprint()
        entry, error = self._take(fingerprint, kind="event_choice", request=request)
        metadata = self._metadata(entry)
        if error is not None:
            return PersonaEventChoiceResult(
                status=PersonaResultStatus.FAILED,
                request_fingerprint=fingerprint,
                metadata=metadata,
                error=error,
            )
        try:
            choice = PersonaEventChoice.model_validate(entry["choice"])
        except (KeyError, ValidationError) as exc:
            return self._event_failure(
                fingerprint,
                metadata,
                f"recorded event choice is malformed: {exc.__class__.__name__}",
            )
        errors = validate_event_choice(choice, request)
        if errors:
            return self._event_failure(fingerprint, metadata, "; ".join(errors))
        return PersonaEventChoiceResult(
            status=PersonaResultStatus.COMPLETED,
            request_fingerprint=fingerprint,
            choice=choice,
            metadata=metadata,
        )

    def _take(
        self,
        fingerprint: str,
        *,
        kind: str,
        request: PersonaDecisionRequest | PersonaEventChoiceRequest,
    ) -> tuple[dict[str, Any], PersonaProviderError | None]:
        entry = self._entries.get(fingerprint)
        if entry is None:
            return {}, _fixture_error("no exact Replay entry for request")
        if fingerprint in self._consumed:
            return entry, _fixture_error("Replay entry is exhausted")
        if entry["kind"] != kind:
            return entry, _fixture_error("Replay entry kind mismatch")
        if (
            entry["persona"] != request.context.persona
            or entry["seed"] != request.context.seed
            or entry["week"] != request.context.state.week
            or entry["state_hash"] != request.state_hash
        ):
            return entry, _fixture_error("Replay entry context mismatch")
        self._consumed.add(fingerprint)
        return entry, None

    def _metadata(self, entry: Mapping[str, Any]) -> PersonaCallMetadata:
        return PersonaCallMetadata(
            provider=self.provider,
            mode=self.mode,
            model="recorded-fixture",
            response_id=str(entry.get("entry_id", "")),
            latency_ms=0,
            parse_status=PersonaParseStatus.PARSED,
        )

    @staticmethod
    def _validate_entry(entry: object, *, index: int) -> dict[str, Any]:
        if not isinstance(entry, dict):
            raise ReplayFixtureError(f"Replay entry {index} must be an object")
        required_strings = ("entry_id", "kind", "fingerprint", "persona", "state_hash")
        for key in required_strings:
            if not isinstance(entry.get(key), str) or not entry[key]:
                raise ReplayFixtureError(f"Replay entry {index} missing {key}")
        if entry["kind"] not in {"decision", "event_choice"}:
            raise ReplayFixtureError(f"Replay entry {index} has invalid kind")
        if len(entry["fingerprint"]) != 64 or len(entry["state_hash"]) != 64:
            raise ReplayFixtureError(f"Replay entry {index} has invalid hash")
        if not isinstance(entry.get("seed"), int) or not isinstance(entry.get("week"), int):
            raise ReplayFixtureError(f"Replay entry {index} has invalid seed/week")
        value_key = "decision" if entry["kind"] == "decision" else "choice"
        if not isinstance(entry.get(value_key), dict):
            raise ReplayFixtureError(f"Replay entry {index} missing {value_key}")
        return dict(entry)

    @staticmethod
    def _decision_failure(
        fingerprint: str,
        metadata: PersonaCallMetadata,
        message: str,
    ) -> PersonaDecisionResult:
        metadata.parse_status = PersonaParseStatus.FAILED
        return PersonaDecisionResult(
            status=PersonaResultStatus.FAILED,
            request_fingerprint=fingerprint,
            metadata=metadata,
            error=_fixture_error(message),
        )

    @staticmethod
    def _event_failure(
        fingerprint: str,
        metadata: PersonaCallMetadata,
        message: str,
    ) -> PersonaEventChoiceResult:
        metadata.parse_status = PersonaParseStatus.FAILED
        return PersonaEventChoiceResult(
            status=PersonaResultStatus.FAILED,
            request_fingerprint=fingerprint,
            metadata=metadata,
            error=_fixture_error(message),
        )


def _fixture_error(message: str) -> PersonaProviderError:
    return PersonaProviderError(
        category=PersonaErrorCategory.FIXTURE_MISMATCH,
        message=message,
        retryable=False,
    )
