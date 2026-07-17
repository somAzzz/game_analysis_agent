"""Frozen interactive playtest profiles shown by Codex before model execution."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .campaign_contract import CampaignPersona
from .persona_gateway import PersonaProvider

PROFILE_SCHEMA = "playtest-session-profiles-v1"


class PlaytestSessionProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9-]+$")
    label: str
    stage: Literal["pipeline", "divergence", "repair_evidence"]
    description: str
    personas: tuple[CampaignPersona, ...] = Field(min_length=1)
    allow_persona_override: bool
    seeds: tuple[int, ...] = Field(min_length=1)
    max_weeks: Literal[20] = 20
    concurrency: int = Field(ge=1, le=4)
    max_calls: int = Field(ge=1)
    repair_target_eligible: bool
    repair_decision_ready: bool

    @model_validator(mode="after")
    def _validate_budget_and_matrix(self) -> PlaytestSessionProfile:
        if len(set(self.personas)) != len(self.personas):
            raise ValueError("profile personas must be unique")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("profile seeds must be unique")
        if self.max_calls < self.worst_case_calls:
            raise ValueError("profile max_calls is below the two-call weekly worst case")
        if self.allow_persona_override and len(self.personas) != 1:
            raise ValueError("only a single-persona profile may allow override")
        if self.repair_decision_ready and (len(self.personas) < 2 or len(self.seeds) < 2):
            raise ValueError("repair evidence requires multiple personas and seeds")
        return self

    @property
    def cell_count(self) -> int:
        return len(self.personas) * len(self.seeds)

    @property
    def worst_case_calls(self) -> int:
        return self.cell_count * self.max_weeks * 2


class PlaytestSessionCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[PROFILE_SCHEMA] = PROFILE_SCHEMA
    profiles: tuple[PlaytestSessionProfile, ...] = Field(min_length=3)

    @model_validator(mode="after")
    def _unique_profiles(self) -> PlaytestSessionCatalog:
        if len({profile.id for profile in self.profiles}) != len(self.profiles):
            raise ValueError("playtest profile ids must be unique")
        return self

    def get(self, profile_id: str) -> PlaytestSessionProfile:
        for profile in self.profiles:
            if profile.id == profile_id:
                return profile
        raise ValueError(f"unknown playtest profile: {profile_id}")


def load_playtest_session_catalog(path: str | Path) -> PlaytestSessionCatalog:
    return PlaytestSessionCatalog.model_validate_json(Path(path).read_text(encoding="utf-8"))


def describe_playtest_profiles(
    catalog: PlaytestSessionCatalog,
    *,
    provider: PersonaProvider,
    single_persona: CampaignPersona = CampaignPersona.NEWBIE,
) -> dict[str, object]:
    profiles = [
        _describe_profile(profile, provider=provider, single_persona=single_persona)
        for profile in catalog.profiles
    ]
    return {
        "schema_version": "playtest-session-options-v1",
        "provider": provider.value,
        "rules": {
            "default_duration": "20 weeks; game completion at state week 20 may use 19 decisions",
            "local_before_live": True,
            "fallback_allowed": False,
            "repair_requires_cross_persona": True,
            "repair_proof_requires_fixed_and_unseen_holdout": True,
            "frontend_url": "http://127.0.0.1:5173/#/playthrough-inspector",
        },
        "recommended_order": ["one-strategy", "six-strategy", "repair-evidence"],
        "profiles": profiles,
    }


def _describe_profile(
    profile: PlaytestSessionProfile,
    *,
    provider: PersonaProvider,
    single_persona: CampaignPersona,
) -> dict[str, object]:
    personas = (single_persona,) if profile.allow_persona_override else profile.personas
    cells = len(personas) * len(profile.seeds)
    environment = {
        "PERSONA_MAX_RUNS": str(cells),
        "PERSONA_MAX_WEEKS": str(profile.max_weeks),
        "PERSONA_MAX_CONCURRENCY": str(profile.concurrency),
        "PERSONA_MAX_CALLS": str(profile.max_calls),
    }
    command = ["scripts/run-persona-campaign", provider.value]
    for persona in personas:
        command.extend(("--persona", persona.value))
    for seed in profile.seeds:
        command.extend(("--seed", str(seed)))
    command.extend(
        (
            "--max-weeks",
            str(profile.max_weeks),
            "--concurrency",
            str(profile.concurrency),
            "--no-resume",
        )
    )
    shell_preview = " ".join(
        [*(f"{key}={value}" for key, value in environment.items()), shlex.join(command)]
    )
    return {
        **profile.model_dump(mode="json"),
        "personas": [persona.value for persona in personas],
        "cell_count": cells,
        "worst_case_calls": cells * profile.max_weeks * 2,
        "environment": environment,
        "command": command,
        "shell_preview": shell_preview,
    }


__all__ = [
    "PROFILE_SCHEMA",
    "PlaytestSessionCatalog",
    "PlaytestSessionProfile",
    "describe_playtest_profiles",
    "load_playtest_session_catalog",
]
