"""Stateful, embeddable multi-turn conversation engine.

``ChatEngine`` is the piece designed to live inside an application: it owns the
message history, holds a system prompt and per-conversation defaults, and
exposes simple ``send`` / ``send_stream`` calls plus history serialization so a
host app can save and restore sessions. The Claude API itself is stateless —
this class is what makes a back-and-forth conversation convenient.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

from .client import ClaudeClient, Message


class ChatEngine:
    """Manage a single multi-turn conversation against a :class:`ClaudeClient`.

    Args:
        client: The client used to talk to Claude.
        system: Optional system prompt for the whole conversation.
        thinking: Enable adaptive thinking for this conversation.
        effort: Effort level (``"low"`` … ``"max"``) for supporting models.
        max_history: If set, keep only the most recent N messages in memory
            (useful for long-running embedded sessions). ``None`` keeps all.
    """

    def __init__(
        self,
        client: ClaudeClient,
        *,
        system: str | None = None,
        thinking: bool | None = None,
        effort: str | None = None,
        max_history: int | None = None,
    ) -> None:
        self.client = client
        self.system = system
        self.thinking = thinking
        self.effort = effort
        self.max_history = max_history
        self._history: list[Message] = []

    # -- history management --------------------------------------------------

    @property
    def history(self) -> list[Message]:
        """The current message history (a live reference; copy before mutating)."""
        return self._history

    def reset(self) -> None:
        """Clear all conversation history."""
        self._history.clear()

    def add_user(self, content: str | list[Any]) -> None:
        """Append a user message without sending it (e.g. to preload context)."""
        self._history.append({"role": "user", "content": content})

    def add_assistant(self, content: str | list[Any]) -> None:
        """Append an assistant message without making a request."""
        self._history.append({"role": "assistant", "content": content})

    def _trim(self) -> None:
        if self.max_history is not None and len(self._history) > self.max_history:
            del self._history[: len(self._history) - self.max_history]

    # -- sending -------------------------------------------------------------

    def _common_kwargs(self) -> dict[str, Any]:
        return {"system": self.system, "thinking": self.thinking, "effort": self.effort}

    def send(self, message: str, **overrides: Any) -> str:
        """Send a user *message*, append the reply to history, and return it."""
        self.add_user(message)
        kwargs = {**self._common_kwargs(), **overrides}
        reply = self.client.chat(self._history, **kwargs)
        self.add_assistant(reply)
        self._trim()
        return reply

    def send_stream(self, message: str, **overrides: Any) -> Iterator[str]:
        """Stream a reply to *message*, accumulating it into history when done."""
        self.add_user(message)
        kwargs = {**self._common_kwargs(), **overrides}
        chunks: list[str] = []
        for delta in self.client.stream(self._history, **kwargs):
            chunks.append(delta)
            yield delta
        self.add_assistant("".join(chunks))
        self._trim()

    async def asend(self, message: str, **overrides: Any) -> str:
        """Async counterpart of :meth:`send`."""
        self.add_user(message)
        kwargs = {**self._common_kwargs(), **overrides}
        reply = await self.client.achat(self._history, **kwargs)
        self.add_assistant(reply)
        self._trim()
        return reply

    async def asend_stream(self, message: str, **overrides: Any) -> AsyncIterator[str]:
        """Async counterpart of :meth:`send_stream`."""
        self.add_user(message)
        kwargs = {**self._common_kwargs(), **overrides}
        chunks: list[str] = []
        async for delta in self.client.astream(self._history, **kwargs):
            chunks.append(delta)
            yield delta
        self.add_assistant("".join(chunks))
        self._trim()

    # -- persistence ---------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the conversation (system prompt + history) to a dict."""
        return {"system": self.system, "history": self._history}

    def save(self, path: str | Path) -> Path:
        """Save the conversation to a JSON file and return the path."""
        if ".." in str(path):
            raise Exception("Invalid file path")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path

    def load(self, path: str | Path) -> None:
        """Replace the current conversation with one loaded from a JSON file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.system = data.get("system", self.system)
        self._history = list(data.get("history", []))
