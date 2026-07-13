"""Pydantic schemas for LLM-call auditing and runtime metadata.

Pattern borrowed from ``fintext_llm/src/schemas/tool_trace.py`` so a
maintainer can swap call audit code between the two projects without
rewriting downstream consumers. ``LLMCall`` is the per-call row emitted
by the agent LLM client; ``ToolExecutionEvent`` / ``ToolBudgetUsage`` track
the tool-calling loop; ``BugFinding`` / ``BoundaryFinding`` /
``ValueFinding`` carry findings emitted by the dedicated analyzer agents.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ToolLoopMode = Literal["native", "json_fallback"]
AnomalyKind = Literal[
    "negative_money",
    "stat_overflow",
    "stat_underflow",
    "non_repeatable_event_repeated",
    "dead_state",
    "week_overflow",
    "single_week_spike",
    "cost_money_exceeds_balance",
    "planned_cost_exceeds_balance",
    "pipeline_stalled",
    "ending_id_empty",
    # Game-semantic invariants (added in v0.2 review action plan T03).
    "crisis_success_ending",
    "social_success_under_survival_crisis",
    "academic_success_with_failed_courses",
    "visa_success_without_registration",
    "testdaf_pass_with_low_language",
    "aps_pass_with_low_aps_knowledge",
    "black_work_without_risk",
    "hunger_ignored_too_long",
    "stress_zero_lock",
    "social_overflow_pattern",
]
AnomalySeverity = Literal["info", "warning", "error", "critical"]


class LLMCall(BaseModel):
    """One chat-completion call made by any agent or analyzer."""

    model_config = ConfigDict(extra="forbid")

    call_id: str
    agent: str
    step_name: str = ""
    provider: str
    model: str
    prompt_text: str = ""
    response_text: str = ""
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int = 0
    error: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class ToolExecutionEvent(BaseModel):
    """One backend-side execution of a model-requested tool call."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    round_id: str
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: Literal["success", "failed"]
    result_summary: str = ""
    latency_ms: int = 0
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ToolBudgetUsage(BaseModel):
    """Budget usage for tool results passed back to the model."""

    model_config = ConfigDict(extra="forbid")

    max_tool_result_chars: int = 12000
    max_total_tool_result_chars: int = 40000
    used_tool_result_chars: int = 0
    truncated_events: int = 0


class AgentRunReport(BaseModel):
    """Summary of one agent run: outputs + LLM calls + tool events."""

    model_config = ConfigDict(extra="forbid")

    agent: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    output_files: list[str] = Field(default_factory=list)
    llm_calls: list[LLMCall] = Field(default_factory=list)
    tool_events: list[ToolExecutionEvent] = Field(default_factory=list)
    budget_usage: ToolBudgetUsage | None = None
    error: str | None = None


class Anomaly(BaseModel):
    """One invariant violation surfaced by :mod:`anomaly_detector`."""

    model_config = ConfigDict(extra="forbid")

    kind: AnomalyKind
    severity: AnomalySeverity = "warning"
    run_id: int
    week: int = -1
    policy: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)
    message: str = ""


class BugFinding(BaseModel):
    """Structured bug-surmise row."""

    model_config = ConfigDict(extra="forbid")

    finding_id: str
    title: str
    severity: AnomalySeverity
    category: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    description: str
    proposed_fix: str = ""


class BoundaryFinding(BaseModel):
    """One extreme-state outcome flagged by the boundary probe."""

    model_config = ConfigDict(extra="forbid")

    finding_id: str
    extreme: str
    severity: AnomalySeverity
    reached_ending: bool = True
    weeks_survived: int = 0
    evidence: dict[str, Any] = Field(default_factory=dict)
    description: str


class ValueFinding(BaseModel):
    """One value / balance observation surfaced by the value reviewer."""

    model_config = ConfigDict(extra="forbid")

    finding_id: str
    scope: Literal[
        "action",
        "event",
        "choice",
        "ending",
        "action_group",
        "crisis_response",
        "ending_contradiction",
        "route",
    ]
    target_id: str
    severity: AnomalySeverity
    metric: str
    value: float
    threshold: float
    description: str


class StateSummary(BaseModel):
    """Compact state slice passed to the LLM player each week."""

    model_config = ConfigDict(extra="allow")

    week: int = 0
    money: int = 0
    blocked_account_balance: int | None = None
    energy: int = 0
    stress: int = 0
    hunger: int = 0
    loneliness: int = 0
    academic_progress: int = 0
    exam_readiness: int | None = None
    language: int = 0
    social: int = 0
    visa_progress: int = 0
    career_progress: int = 0
    gpa_score: int | None = None
    annual_work_half_days: int | None = None
    university_tier: str | None = None
    flags: dict[str, bool] = Field(default_factory=dict)


class ActionBrief(BaseModel):
    """Action facts needed for one weekly decision."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str = ""
    description: str = ""
    type: str = ""
    cost: dict[str, int] = Field(default_factory=dict)
    effects: dict[str, int] = Field(default_factory=dict)
    requirements: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    risk_tags: list[str] = Field(default_factory=list)
    cooldown_group: str | None = None
    max_per_week: int | None = None


class EventChoiceBrief(BaseModel):
    """Event choice facts needed for one decision."""

    model_config = ConfigDict(extra="forbid")

    choice_id: str
    text: str = ""
    success_rate: float | None = None
    requirements: dict[str, Any] = Field(default_factory=dict)
    success_effects: dict[str, int] = Field(default_factory=dict)
    failure_effects: dict[str, int] = Field(default_factory=dict)


class RiskBrief(BaseModel):
    """Small risk row shown to the player agent."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str = ""
    score: int | None = Field(default=None, ge=0, le=100)
    severity: Literal["low", "medium", "high", "critical"]
    reason: str
    suggested_action_types: list[str] = Field(default_factory=list)
    suggested_action_ids: list[str] = Field(default_factory=list)


class RiskGuidanceMetadata(BaseModel):
    """Provenance for the risk rows included in a weekly prompt."""

    model_config = ConfigDict(extra="forbid")

    source: Literal["game_risk_evaluator", "python_fallback"]
    evaluator: str
    generated_for_week: int = Field(ge=0)
    contract_version: str = ""
    fallback_reason: str = ""


class WeekMemory(BaseModel):
    """One compressed historical week for player memory."""

    model_config = ConfigDict(extra="forbid")

    week: int
    actions: list[str] = Field(default_factory=list)
    event: str = ""
    rationale: str = ""
    delta: dict[str, int] = Field(default_factory=dict)


class PlayMemory(BaseModel):
    """Longitudinal memory shown to the LLM instead of raw history."""

    model_config = ConfigDict(extra="forbid")

    persona: str
    route_commitment: str = ""
    long_term_goal: str = ""
    known_deadlines: list[str] = Field(default_factory=list)
    unresolved_risks: list[str] = Field(default_factory=list)
    important_flags: dict[str, bool] = Field(default_factory=dict)
    repeated_actions: dict[str, int] = Field(default_factory=dict)
    last_5_weeks: list[WeekMemory] = Field(default_factory=list)
    mistakes: list[str] = Field(default_factory=list)
    successful_patterns: list[str] = Field(default_factory=list)


class WeekContext(BaseModel):
    """Complete-but-compact context pack for one weekly LLM decision."""

    model_config = ConfigDict(extra="forbid")

    game_version: str = ""
    seed: int
    difficulty: str
    scenario: str
    max_action_slots: int = 4
    persona: str
    persona_strategy: dict[str, Any] = Field(default_factory=dict)
    state: StateSummary
    top_risks: list[RiskBrief] = Field(default_factory=list)
    risk_guidance: RiskGuidanceMetadata
    available_actions: list[ActionBrief] = Field(default_factory=list)
    current_event_id: str = ""
    event_choices: list[EventChoiceBrief] = Field(default_factory=list)
    memory: PlayMemory


class PlayerDecision(BaseModel):
    """Structured LLM player decision for one week."""

    model_config = ConfigDict(extra="forbid")

    week: int
    persona: str
    strategic_goal: str = Field(default="", max_length=160)
    actions: list[str] = Field(min_length=1, max_length=4)
    event_choice_id: str = ""
    risk_awareness: list[str] = Field(default_factory=list, max_length=5)
    expected_tradeoff: str = Field(default="", max_length=240)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("actions")
    @classmethod
    def _dedupe_actions(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        cleaned: list[str] = []
        for item in value:
            action_id = str(item).strip()
            if action_id and action_id not in seen:
                cleaned.append(action_id)
                seen.add(action_id)
        return cleaned


class DecisionValidation(BaseModel):
    """Validation outcome for one player decision."""

    model_config = ConfigDict(extra="forbid")

    valid: bool
    errors: list[str] = Field(default_factory=list)
    repair_count: int = 0
    fallback_used: bool = False


__all__ = [
    "AgentRunReport",
    "Anomaly",
    "AnomalyKind",
    "AnomalySeverity",
    "BoundaryFinding",
    "BugFinding",
    "LLMCall",
    "ActionBrief",
    "ToolBudgetUsage",
    "ToolExecutionEvent",
    "ToolLoopMode",
    "DecisionValidation",
    "EventChoiceBrief",
    "PlayerDecision",
    "PlayMemory",
    "RiskBrief",
    "RiskGuidanceMetadata",
    "StateSummary",
    "ValueFinding",
    "WeekContext",
    "WeekMemory",
]
