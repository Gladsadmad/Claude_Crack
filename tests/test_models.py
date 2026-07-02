from claude_crack import models


def test_default_model():
    assert models.DEFAULT_MODEL == "claude-opus-4-8"
    assert models.resolve_model(None) == "claude-opus-4-8"


def test_aliases():
    assert models.resolve_model("opus") == "claude-opus-4-8"
    assert models.resolve_model("sonnet") == "claude-sonnet-4-6"
    assert models.resolve_model("haiku") == "claude-haiku-4-5"
    assert models.resolve_model("FAST") == "claude-haiku-4-5"


def test_unknown_passthrough():
    # Unknown IDs return unchanged so future models keep working.
    assert models.resolve_model("claude-future-9") == "claude-future-9"
    assert models.get_model_info("claude-future-9") is None


def test_get_model_info():
    info = models.get_model_info("opus")
    assert info is not None
    assert info.id == "claude-opus-4-8"
    assert info.adaptive_thinking is True
    assert info.supports_effort is True
    assert info.max_output == 128_000


def test_haiku_capabilities():
    info = models.get_model_info("haiku")
    assert info is not None
    assert info.supports_effort is False  # effort errors on Haiku 4.5


def test_known_models_nonempty():
    ids = {m.id for m in models.known_models()}
    assert "claude-opus-4-8" in ids
    assert "claude-fable-5" in ids
