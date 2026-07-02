import importlib

import pytest

from claude_crack import config
from claude_crack.exceptions import APIKeyMissingError


def test_config_dir_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(config.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert config.config_dir() == tmp_path / "claude_crack"


def test_config_dir_macos(monkeypatch):
    monkeypatch.setattr(config.sys, "platform", "darwin")
    expected = config.Path.home() / "Library" / "Application Support" / "claude_crack"
    assert config.config_dir() == expected


def test_config_dir_linux_xdg(monkeypatch, tmp_path):
    monkeypatch.setattr(config.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert config.config_dir() == tmp_path / "claude_crack"


def test_settings_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    settings = config.Settings(model="claude-sonnet-4-6", effort="medium", thinking=True)
    settings.api_key = "secret"  # must not be persisted
    settings.save(path)

    raw = path.read_text(encoding="utf-8")
    assert "secret" not in raw

    loaded = config.Settings.load(path)
    assert loaded.model == "claude-sonnet-4-6"
    assert loaded.effort == "medium"
    assert loaded.thinking is True
    assert loaded.api_key is None


def test_settings_load_missing_returns_defaults(tmp_path):
    loaded = config.Settings.load(tmp_path / "does-not-exist.json")
    assert loaded.model == config.DEFAULT_MODEL


def test_resolve_api_key_precedence(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_CRACK_API_KEY", raising=False)
    assert config.resolve_api_key("explicit") == "explicit"

    settings = config.Settings(api_key="from-settings")
    assert config.resolve_api_key(None, settings) == "from-settings"

    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
    assert config.resolve_api_key() == "from-env"


def test_resolve_api_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_CRACK_API_KEY", raising=False)
    with pytest.raises(APIKeyMissingError):
        config.resolve_api_key()


def test_module_reimport_stable():
    # Guards against import-time side effects breaking re-import.
    importlib.reload(config)
