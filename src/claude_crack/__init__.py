"""claude-crack — a small, cross-platform, embeddable client for Claude.

Quick start::

    from claude_crack import ClaudeClient, ChatEngine

    client = ClaudeClient()              # reads ANTHROPIC_API_KEY from the env
    chat = ChatEngine(client, system="You are concise.")
    print(chat.send("Hello!"))

See the README for streaming, async, and embedding examples.
"""

from __future__ import annotations

from .client import ClaudeClient, Message
from .config import Settings, config_dir, config_path, resolve_api_key
from .conversation import ChatEngine
from .exceptions import (
    APIKeyMissingError,
    ClaudeAPIError,
    ClaudeCrackError,
    ConfigError,
    RefusalError,
)
from .models import DEFAULT_MODEL, ModelInfo, get_model_info, known_models, resolve_model

__version__ = "0.1.0"

__all__ = [
    "ClaudeClient",
    "ChatEngine",
    "Message",
    "Settings",
    "config_dir",
    "config_path",
    "resolve_api_key",
    "ClaudeCrackError",
    "ConfigError",
    "APIKeyMissingError",
    "ClaudeAPIError",
    "RefusalError",
    "DEFAULT_MODEL",
    "ModelInfo",
    "get_model_info",
    "known_models",
    "resolve_model",
    "__version__",
]
