"""Cross-platform configuration storage and API-key resolution.

This module gives the package the "fits inside an app" property: it locates a
per-user config directory using the right convention for each OS, persists a
small JSON settings file there, and resolves the API key from the standard
places an embedding application would expect.

No third-party dependency is used for path resolution so the package stays
light and works the same on Windows, macOS, and Linux.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .exceptions import APIKeyMissingError
from .models import DEFAULT_MODEL

_APP_NAME = "claude_crack"
_CONFIG_FILE = "config.json"

#: Environment variables checked (in order) when resolving an API key.
API_KEY_ENV_VARS = ("CLAUDE_CRACK_API_KEY", "ANTHROPIC_API_KEY")


def config_dir() -> Path:
    """Return the per-user config directory for the current platform.

    * Windows: ``%APPDATA%\\claude_crack``
    * macOS:   ``~/Library/Application Support/claude_crack``
    * Linux/other: ``$XDG_CONFIG_HOME/claude_crack`` or ``~/.config/claude_crack``

    The directory is not created here; :meth:`Settings.save` creates it lazily.
    """
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / _APP_NAME


def config_path() -> Path:
    """Return the full path to the settings JSON file."""
    return config_dir() / _CONFIG_FILE


@dataclass
class Settings:
    """User-tunable defaults persisted to the config file.

    ``api_key`` is intentionally *not* persisted to disk by default — secrets
    belong in the environment or an OS keychain, not a plaintext JSON file. It
    is included here only so an app can pass one in memory.
    """

    model: str = DEFAULT_MODEL
    system_prompt: str | None = None
    max_tokens: int = 0  # 0 → pick a sensible default per call (see ClaudeClient)
    thinking: bool = False
    effort: str = "high"
    extra: dict = field(default_factory=dict)

    # Not serialized to disk.
    api_key: str | None = None

    @classmethod
    def load(cls, path: Path | None = None) -> Settings:
        """Load settings from disk, falling back to defaults when absent."""
        path = path or config_path()
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        known = {f for f in cls.__dataclass_fields__ if f != "api_key"}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self, path: Path | None = None) -> Path:
        """Persist settings to disk (excluding ``api_key``) and return the path."""
        path = path or config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v for k, v in asdict(self).items() if k != "api_key"}
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return path


def resolve_api_key(explicit: str | None = None, settings: Settings | None = None) -> str:
    """Resolve an API key from, in order: explicit arg, settings, environment.

    Raises :class:`APIKeyMissingError` if none is found.
    """
    if explicit:
        return explicit
    if settings and settings.api_key:
        return settings.api_key
    for var in API_KEY_ENV_VARS:
        value = os.environ.get(var)
        if value:
            return value
    raise APIKeyMissingError(
        "No Claude API key found. Set the ANTHROPIC_API_KEY environment variable, "
        "or pass api_key=... to the client."
    )
