"""Registry of Claude models and their relevant capabilities.

This is a small, hand-maintained snapshot used to make sensible defaults
(thinking mode, effort, output limits) without a network round-trip. For live
capability data, query the Anthropic Models API
(``client.models.retrieve(...)``); see :meth:`ClaudeClient.list_models`.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Default model used when the caller does not specify one.
DEFAULT_MODEL = "claude-opus-4-8"


@dataclass(frozen=True)
class ModelInfo:
    """Static capability snapshot for a single Claude model."""

    id: str
    display_name: str
    context_window: int
    max_output: int
    #: Whether the model uses adaptive thinking (``{"type": "adaptive"}``).
    #: Older models that take ``budget_tokens`` are marked ``False``.
    adaptive_thinking: bool
    #: Whether the model accepts the ``output_config.effort`` parameter.
    supports_effort: bool


# Snapshot current as of 2026-06. Keep IDs exact — do not append date suffixes.
_MODELS: dict[str, ModelInfo] = {
    "claude-fable-5": ModelInfo(
        "claude-fable-5", "Claude Fable 5", 1_000_000, 128_000, True, True
    ),
    "claude-opus-4-8": ModelInfo(
        "claude-opus-4-8", "Claude Opus 4.8", 1_000_000, 128_000, True, True
    ),
    "claude-opus-4-7": ModelInfo(
        "claude-opus-4-7", "Claude Opus 4.7", 1_000_000, 128_000, True, True
    ),
    "claude-opus-4-6": ModelInfo(
        "claude-opus-4-6", "Claude Opus 4.6", 1_000_000, 128_000, True, True
    ),
    "claude-sonnet-4-6": ModelInfo(
        "claude-sonnet-4-6", "Claude Sonnet 4.6", 1_000_000, 64_000, True, True
    ),
    "claude-haiku-4-5": ModelInfo(
        "claude-haiku-4-5", "Claude Haiku 4.5", 200_000, 64_000, True, False
    ),
}

#: Friendly aliases users commonly type, mapped to canonical model IDs.
_ALIASES: dict[str, str] = {
    "fable": "claude-fable-5",
    "opus": "claude-opus-4-8",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5",
    "fast": "claude-haiku-4-5",
    "cheap": "claude-haiku-4-5",
}


def resolve_model(name: str | None) -> str:
    """Resolve an alias or model ID to a canonical model ID.

    Unknown strings are returned unchanged so newer models keep working before
    this registry is updated.
    """
    if not name:
        return DEFAULT_MODEL
    key = name.strip().lower()
    return _ALIASES.get(key, name)


def get_model_info(model: str) -> ModelInfo | None:
    """Return the :class:`ModelInfo` for *model*, or ``None`` if unknown."""
    return _MODELS.get(resolve_model(model))


def known_models() -> list[ModelInfo]:
    """Return all models in the local registry."""
    return list(_MODELS.values())
