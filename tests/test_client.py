"""ClaudeClient request-building tests.

These exercise the pure parameter-shaping logic (thinking/effort gating, output
caps, system prompt) without making any network call. The constructor only
instantiates the SDK client object, which performs no I/O.
"""

from __future__ import annotations

import pytest

anthropic = pytest.importorskip("anthropic")

from claude_crack import ClaudeClient  # noqa: E402

MESSAGES = [{"role": "user", "content": "hi"}]


def make_client(**kwargs) -> ClaudeClient:
    return ClaudeClient(api_key="test-key", **kwargs)


def _params(client: ClaudeClient, **kw):
    defaults = dict(
        model=None,
        system=None,
        max_tokens=None,
        thinking=None,
        effort=None,
        streaming=False,
        extra=None,
    )
    defaults.update(kw)
    return client._build_params(MESSAGES, **defaults)


def test_default_model_and_max_tokens():
    client = make_client()
    params = _params(client)
    assert params["model"] == "claude-opus-4-8"
    assert params["max_tokens"] == 16_000  # non-streaming default
    assert "thinking" not in params  # off unless requested


def test_streaming_default_max_tokens():
    client = make_client()
    params = _params(client, streaming=True)
    assert params["max_tokens"] == 64_000


def test_thinking_and_effort_for_supported_model():
    client = make_client()
    params = _params(client, thinking=True, effort="high")
    assert params["thinking"] == {"type": "adaptive", "display": "summarized"}
    assert params["output_config"] == {"effort": "high"}


def test_effort_gated_off_for_haiku():
    client = make_client(model="haiku")
    params = _params(client, thinking=True, effort="high")
    # Haiku doesn't support effort, so it must be omitted.
    assert "output_config" not in params
    # Haiku supports adaptive thinking, so that stays.
    assert params["thinking"]["type"] == "adaptive"


def test_max_tokens_capped_to_model_limit():
    client = make_client(model="sonnet")  # 64k output cap
    params = _params(client, max_tokens=999_999)
    assert params["max_tokens"] == 64_000


def test_system_prompt_included():
    client = make_client()
    params = _params(client, system="be terse")
    assert params["system"] == "be terse"


def test_alias_resolution_in_request():
    client = make_client()
    params = _params(client, model="sonnet")
    assert params["model"] == "claude-sonnet-4-6"


def test_extract_text():
    class Block:
        def __init__(self, type_, text=""):
            self.type = type_
            self.text = text

    client = make_client()
    blocks = [Block("thinking"), Block("text", "Hello "), Block("text", "world")]
    assert client._extract_text(blocks) == "Hello world"
