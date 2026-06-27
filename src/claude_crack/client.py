"""The Claude client wrapper — sync and async, with sensible cross-platform defaults.

``ClaudeClient`` is a thin, opinionated layer over the official ``anthropic`` SDK.
It picks the right thinking/effort/output settings per model, normalizes errors
into :mod:`claude_crack.exceptions`, and exposes simple ``chat`` / ``stream``
methods that work with plain message dicts so the library drops into any app.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any

from . import models
from .config import Settings, resolve_api_key
from .exceptions import ClaudeAPIError, RefusalError

# Message is the same shape the Anthropic Messages API expects:
# {"role": "user" | "assistant", "content": str | list[block]}
Message = dict[str, Any]

# Default output ceilings. Streaming gets more room because it isn't subject to
# the SDK's non-streaming HTTP-timeout guard.
_DEFAULT_MAX_TOKENS = 16_000
_DEFAULT_STREAM_MAX_TOKENS = 64_000


class ClaudeClient:
    """A small, embeddable Claude client.

    Args:
        api_key: API key. Falls back to settings, then ``ANTHROPIC_API_KEY`` /
            ``CLAUDE_CRACK_API_KEY`` environment variables.
        model: Model ID or alias (e.g. ``"opus"``, ``"sonnet"``). Defaults to
            ``claude-opus-4-8``.
        settings: Optional :class:`~claude_crack.config.Settings` providing
            defaults for model, system prompt, thinking, and effort.
        **client_kwargs: Forwarded to ``anthropic.Anthropic`` (e.g. ``timeout``,
            ``max_retries``, ``base_url``).
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str | None = None,
        settings: Settings | None = None,
        **client_kwargs: Any,
    ) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - import guard
            raise ClaudeAPIError(
                "The 'anthropic' package is required. Install it with "
                "'pip install claude-crack' (it is a dependency)."
            ) from exc

        self._anthropic = anthropic
        self.settings = settings or Settings()
        self.model = models.resolve_model(model or self.settings.model)
        self._api_key = resolve_api_key(api_key, self.settings)
        self._client_kwargs = client_kwargs
        self._sync = anthropic.Anthropic(api_key=self._api_key, **client_kwargs)
        self._async = None  # created lazily on first async use

    # -- request building ----------------------------------------------------

    def _build_params(
        self,
        messages: Sequence[Message],
        *,
        model: str | None,
        system: str | None,
        max_tokens: int | None,
        thinking: bool | None,
        effort: str | None,
        streaming: bool,
        extra: dict[str, Any] | None,
    ) -> dict[str, Any]:
        resolved_model = models.resolve_model(model or self.model)
        info = models.get_model_info(resolved_model)

        if max_tokens is None:
            max_tokens = self.settings.max_tokens or (
                _DEFAULT_STREAM_MAX_TOKENS if streaming else _DEFAULT_MAX_TOKENS
            )
        if info is not None:
            max_tokens = min(max_tokens, info.max_output)

        params: dict[str, Any] = {
            "model": resolved_model,
            "max_tokens": max_tokens,
            "messages": list(messages),
        }

        system = system if system is not None else self.settings.system_prompt
        if system:
            params["system"] = system

        want_thinking = self.settings.thinking if thinking is None else thinking
        # Adaptive thinking is only valid on models that support it; sending it
        # to an older model would 400, so we gate on the registry.
        if want_thinking and (info is None or info.adaptive_thinking):
            params["thinking"] = {"type": "adaptive", "display": "summarized"}

        chosen_effort = effort or self.settings.effort
        if chosen_effort and (info is None or info.supports_effort):
            params["output_config"] = {"effort": chosen_effort}

        if extra:
            params.update(extra)
        return params

    @staticmethod
    def _extract_text(content: Sequence[Any]) -> str:
        return "".join(
            getattr(block, "text", "") for block in content if getattr(block, "type", "") == "text"
        )

    def _check_refusal(self, response: Any) -> None:
        if getattr(response, "stop_reason", None) == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None) if details else None
            raise RefusalError(
                "The model declined to respond to this request.", category=category
            )

    # -- sync API ------------------------------------------------------------

    def chat(
        self,
        messages: Sequence[Message],
        *,
        model: str | None = None,
        system: str | None = None,
        max_tokens: int | None = None,
        thinking: bool | None = None,
        effort: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """Send *messages* and return the assistant's text reply.

        Raises :class:`~claude_crack.exceptions.RefusalError` if the model
        declined, or :class:`~claude_crack.exceptions.ClaudeAPIError` on an
        API/transport failure.
        """
        params = self._build_params(
            messages,
            model=model,
            system=system,
            max_tokens=max_tokens,
            thinking=thinking,
            effort=effort,
            streaming=False,
            extra=extra,
        )
        try:
            response = self._sync.messages.create(**params)
        except self._anthropic.APIError as exc:
            raise self._wrap_api_error(exc) from exc
        self._check_refusal(response)
        return self._extract_text(response.content)

    def stream(
        self,
        messages: Sequence[Message],
        *,
        model: str | None = None,
        system: str | None = None,
        max_tokens: int | None = None,
        thinking: bool | None = None,
        effort: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Iterator[str]:
        """Stream the assistant's reply, yielding text deltas as they arrive."""
        params = self._build_params(
            messages,
            model=model,
            system=system,
            max_tokens=max_tokens,
            thinking=thinking,
            effort=effort,
            streaming=True,
            extra=extra,
        )
        try:
            with self._sync.messages.stream(**params) as stream:
                yield from stream.text_stream
                self._check_refusal(stream.get_final_message())
        except self._anthropic.APIError as exc:
            raise self._wrap_api_error(exc) from exc

    # -- async API -----------------------------------------------------------

    def _ensure_async(self) -> Any:
        if self._async is None:
            self._async = self._anthropic.AsyncAnthropic(
                api_key=self._api_key, **self._client_kwargs
            )
        return self._async

    async def achat(
        self,
        messages: Sequence[Message],
        *,
        model: str | None = None,
        system: str | None = None,
        max_tokens: int | None = None,
        thinking: bool | None = None,
        effort: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """Async counterpart of :meth:`chat`."""
        client = self._ensure_async()
        params = self._build_params(
            messages,
            model=model,
            system=system,
            max_tokens=max_tokens,
            thinking=thinking,
            effort=effort,
            streaming=False,
            extra=extra,
        )
        try:
            response = await client.messages.create(**params)
        except self._anthropic.APIError as exc:
            raise self._wrap_api_error(exc) from exc
        self._check_refusal(response)
        return self._extract_text(response.content)

    async def astream(
        self,
        messages: Sequence[Message],
        *,
        model: str | None = None,
        system: str | None = None,
        max_tokens: int | None = None,
        thinking: bool | None = None,
        effort: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        """Async counterpart of :meth:`stream`."""
        client = self._ensure_async()
        params = self._build_params(
            messages,
            model=model,
            system=system,
            max_tokens=max_tokens,
            thinking=thinking,
            effort=effort,
            streaming=True,
            extra=extra,
        )
        try:
            async with client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text
                self._check_refusal(await stream.get_final_message())
        except self._anthropic.APIError as exc:
            raise self._wrap_api_error(exc) from exc

    # -- helpers -------------------------------------------------------------

    def list_models(self) -> list[Any]:
        """Return live model metadata from the Anthropic Models API."""
        try:
            return list(self._sync.models.list())
        except self._anthropic.APIError as exc:
            raise self._wrap_api_error(exc) from exc

    def _wrap_api_error(self, exc: Any) -> ClaudeAPIError:
        status = getattr(exc, "status_code", None)
        message = getattr(exc, "message", None) or str(exc)
        return ClaudeAPIError(message, status_code=status)

    def close(self) -> None:
        """Release underlying HTTP resources."""
        for client in (self._sync, self._async):
            if client is not None:
                try:
                    client.close()
                except Exception:  # pragma: no cover - best effort
                    pass

    def __enter__(self) -> ClaudeClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
