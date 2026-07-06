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

from pydantic import BaseModel, ConfigDict, Field

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


__all__ = [
    "AgentRunReport",
    "Anomaly",
    "AnomalyKind",
    "AnomalySeverity",
    "BoundaryFinding",
    "BugFinding",
    "LLMCall",
    "ToolBudgetUsage",
    "ToolExecutionEvent",
    "ToolLoopMode",
    "ValueFinding",
]
