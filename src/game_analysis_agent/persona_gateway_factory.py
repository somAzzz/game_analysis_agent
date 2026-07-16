"""Build exactly one governed persona gateway after validated preflight."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .llm_client import LocalLLMClient
from .local_persona_gateway import LocalChatPersonaGateway
from .openai_persona_gateway import OpenAIResponsesPersonaGateway
from .persona_gateway import PersonaDecisionGateway, PersonaProvider
from .persona_runtime import (
    GovernedPersonaGateway,
    PersonaCancellationToken,
    PersonaProviderSelection,
    PersonaRuntimeConfigurationError,
    PersonaRuntimeSettings,
)
from .recorded_persona_gateway import RecordedPersonaGateway


@dataclass(frozen=True)
class BuiltPersonaGateway:
    selection: PersonaProviderSelection
    gateway: GovernedPersonaGateway


def build_persona_gateway(
    settings: PersonaRuntimeSettings,
    *,
    project_root: str | Path,
    local_llm: LocalLLMClient | None = None,
    openai_client: Any | None = None,
    cancellation: PersonaCancellationToken | None = None,
) -> BuiltPersonaGateway:
    """Resolve once and construct that provider only; never install a fallback."""

    selection = settings.resolve_provider()
    provider = selection.selected
    gateway: PersonaDecisionGateway
    if provider == PersonaProvider.REPLAY:
        manifest = Path(project_root) / settings.replay_manifest
        gateway = RecordedPersonaGateway.from_manifest(
            manifest, project_root=project_root
        )
    elif provider == PersonaProvider.OPENAI:
        if settings.openai_api_key is None:  # protected by resolve_provider
            raise PersonaRuntimeConfigurationError("OpenAI key missing after preflight")
        gateway = OpenAIResponsesPersonaGateway(
            api_key=settings.openai_api_key.get_secret_value(),
            model=settings.openai_model,
            client=openai_client,
        )
    else:
        if local_llm is None:
            raise PersonaRuntimeConfigurationError(
                f"PERSONA_PROVIDER={provider.value} requires a configured local chat client"
            )
        actual = str(getattr(local_llm, "provider", ""))
        if actual != provider.value:
            raise PersonaRuntimeConfigurationError(
                f"persona provider {provider.value} does not match local client {actual or '(unset)'}"
            )
        gateway = LocalChatPersonaGateway(local_llm)
    return BuiltPersonaGateway(
        selection=selection,
        gateway=GovernedPersonaGateway(
            gateway,
            limits=settings.limits,
            cancellation=cancellation,
        ),
    )


__all__ = ["BuiltPersonaGateway", "build_persona_gateway"]
