"""Narrow interactive-player integration tests across persona providers."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from game_analysis_agent.agents.interactive_player import InteractivePlayerAgent
from game_analysis_agent.local_persona_gateway import LocalChatPersonaGateway
from game_analysis_agent.openai_persona_gateway import OpenAIResponsesPersonaGateway
from game_analysis_agent.persona_gateway import (
    PersonaDecisionRequest,
    PersonaErrorCategory,
    PersonaProvider,
    PersonaResultStatus,
)
from game_analysis_agent.persona_gateway_factory import build_persona_gateway
from game_analysis_agent.persona_runtime import PersonaRuntimeSettings
from game_analysis_agent.recorded_persona_gateway import RecordedPersonaGateway
from game_analysis_agent.schemas import LLMCall, PlayerDecision, WeekContext
from game_analysis_agent.settings import Settings

ROOT = Path(__file__).resolve().parents[1]


class _Responses:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)

    def parse(self, **_kwargs):
        return self.outcomes.pop(0)


class _OpenAIClient:
    def __init__(self, outcomes: list[object]) -> None:
        self.responses = _Responses(outcomes)


class _LocalLLM:
    provider = "vllm"
    model = "local-test"

    def __init__(self, contents: list[str]) -> None:
        self.contents = list(contents)
        self.settings = Settings()
        self.calls = 0

    def chat(self, messages, *, agent, step_name, max_tokens, temperature):  # noqa: ANN001
        del messages, max_tokens, temperature
        self.calls += 1
        content = self.contents.pop(0)
        return content, LLMCall(
            call_id=f"local-{self.calls}",
            agent=agent,
            step_name=step_name,
            provider=self.provider,
            model=self.model,
            prompt_text="",
            response_text=content,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            latency_ms=1,
        )


def _context() -> WeekContext:
    return WeekContext.model_validate(
        {
            "game_version": "test",
            "seed": 42,
            "difficulty": "normal",
            "scenario": "default_first_semester",
            "persona": "newbie",
            "state": {"week": 1, "money": 420, "stress": 55},
            "risk_guidance": {
                "source": "game_risk_evaluator",
                "evaluator": "RiskEvaluator.get_top_risks",
                "generated_for_week": 1,
                "contract_version": "1.0",
            },
            "available_actions": [
                {"id": "budget_call", "name": "Budget call"},
                {"id": "rest_at_home", "name": "Rest"},
            ],
            "current_event_id": "rent_pressure",
            "event_choices": [
                {"choice_id": "rent_pressure.pay_now", "text": "Pay now"},
                {
                    "choice_id": "rent_pressure.ask_extension",
                    "text": "Ask extension",
                },
            ],
            "memory": {"persona": "newbie"},
        }
    )


def _decision(*, action: str = "budget_call") -> PlayerDecision:
    return PlayerDecision(
        week=1,
        persona="newbie",
        strategic_goal="protect cashflow",
        actions=[action],
        event_choice_id="rent_pressure.ask_extension",
        risk_awareness=["money"],
        expected_tradeoff="use one action slot to preserve cash",
        confidence=0.8,
    )


def _response(parsed: object):
    return SimpleNamespace(
        id="resp-test",
        model="gpt-test",
        output=[
            SimpleNamespace(
                type="message",
                content=[SimpleNamespace(type="output_text", parsed=parsed, refusal=None)],
            )
        ],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5, total_tokens=15),
    )


def _agent(gateway, llm=None) -> InteractivePlayerAgent:  # noqa: ANN001
    return InteractivePlayerAgent(
        llm=llm,  # type: ignore[arg-type]
        prompts_root=ROOT / "prompts",
        settings=Settings(),
        persona="newbie",
        seed=42,
        persona_gateway=gateway,
    )


def _run_gateway(agent: InteractivePlayerAgent) -> tuple[list[str], str]:
    context = _context()
    decision, validation, _calls = agent._decide_one_week(
        week=1,
        context_pack=context,
        system_prompt="unused",
        probe=None,  # type: ignore[arg-type]
    )
    choice, event_validation, _event_calls = agent._decide_event_choice(
        week=1,
        context_pack=context,
        selected_actions=decision.actions,
    )
    assert validation.valid is True
    assert event_validation.valid is True
    return decision.actions, choice


def test_replay_openai_and_local_share_identical_interactive_semantics() -> None:
    replay = RecordedPersonaGateway.from_manifest(
        ROOT / "config/build_week_2026_replay.json", project_root=ROOT
    )
    openai = OpenAIResponsesPersonaGateway(
        api_key="sk-test",
        client=_OpenAIClient(
            [
                _response(_decision()),
                _response(
                    {
                        "week": 1,
                        "persona": "newbie",
                        "event_id": "rent_pressure",
                        "event_choice_id": "rent_pressure.ask_extension",
                    }
                ),
            ]
        ),
    )
    local_llm = _LocalLLM(
        [_decision().model_dump_json(), '{"event_choice_id":"rent_pressure.ask_extension"}']
    )
    local = LocalChatPersonaGateway(local_llm)  # type: ignore[arg-type]

    agents = [_agent(item) for item in (replay, openai, local)]
    outcomes = [_run_gateway(agent) for agent in agents]

    assert outcomes == [
        (["budget_call"], "rent_pressure.ask_extension"),
        (["budget_call"], "rent_pressure.ask_extension"),
        (["budget_call"], "rent_pressure.ask_extension"),
    ]
    assert [
        agent._persona_call_records[0]["metadata"]["provider"]  # noqa: SLF001
        for agent in agents
    ] == ["replay", "openai", "vllm"]


def test_local_unknown_action_fails_after_one_shared_repair() -> None:
    llm = _LocalLLM([_decision(action="ghost").model_dump_json()] * 2)
    gateway = LocalChatPersonaGateway(llm)  # type: ignore[arg-type]

    result = gateway.decide(
        PersonaDecisionRequest.from_context(_context(), request_id="newbie-42-w1-invalid")
    )

    assert result.status == PersonaResultStatus.FAILED
    assert result.error is not None
    assert result.error.category == PersonaErrorCategory.INVALID_DECISION
    assert result.metadata.provider == PersonaProvider.VLLM
    assert result.metadata.attempt_count == 2
    assert result.metadata.usage.total_tokens == 30
    assert llm.calls == 2


def test_local_normalizes_compact_model_variations_without_hiding_invalid_ids() -> None:
    llm = _LocalLLM(
        [
            json.dumps(
                {
                    "actions": "budget_call",
                    "event_choice_id": "rent_pressure.ask_extension",
                    "rationale": "protect cashflow",
                    "risk_awareness": "money",
                    "confidence": "0.8",
                    "ignored_commentary": "not part of the contract",
                }
            )
        ]
    )
    gateway = LocalChatPersonaGateway(llm)  # type: ignore[arg-type]

    result = gateway.decide(
        PersonaDecisionRequest.from_context(_context(), request_id="newbie-42-w1-normalized")
    )

    assert result.status == PersonaResultStatus.COMPLETED
    assert result.decision is not None
    assert result.decision.actions == ["budget_call"]
    assert result.decision.risk_awareness == ["money"]
    assert result.decision.confidence == 0.8


def test_local_discards_stale_action_when_another_legal_action_remains() -> None:
    payload = _decision().model_dump(mode="json")
    payload["actions"] = ["budget_call", "stale_action"]
    llm = _LocalLLM([json.dumps(payload)])
    gateway = LocalChatPersonaGateway(llm)  # type: ignore[arg-type]

    result = gateway.decide(
        PersonaDecisionRequest.from_context(_context(), request_id="newbie-42-w1-stale-action")
    )

    assert result.status == PersonaResultStatus.COMPLETED
    assert result.decision is not None
    assert result.decision.actions == ["budget_call"]


def test_factory_defaults_to_governed_hash_pinned_replay() -> None:
    built = build_persona_gateway(PersonaRuntimeSettings.from_env({}), project_root=ROOT)

    assert built.selection.selected == PersonaProvider.REPLAY
    result = built.gateway.decide(
        PersonaDecisionRequest.from_context(_context(), request_id="newbie-42-w1-decision")
    )
    assert result.status == PersonaResultStatus.COMPLETED
    assert built.gateway.calls_used == 1


def test_factory_builds_only_the_explicit_openai_provider() -> None:
    settings = PersonaRuntimeSettings.from_env(
        {"PERSONA_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test"}
    )
    built = build_persona_gateway(
        settings,
        project_root=ROOT,
        openai_client=_OpenAIClient([_response(_decision())]),
    )

    assert built.selection.selected == PersonaProvider.OPENAI
    assert built.gateway.provider == PersonaProvider.OPENAI
