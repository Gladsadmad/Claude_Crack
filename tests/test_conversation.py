"""ChatEngine tests using a fake client — no network or API key required."""

from __future__ import annotations

import pytest

from claude_crack import ChatEngine


class FakeClient:
    """Records calls and returns canned replies; mimics ClaudeClient's surface."""

    def __init__(self, reply: str = "ok"):
        self.reply = reply
        self.calls: list[dict] = []

    def chat(self, messages, **kwargs):
        self.calls.append({"messages": list(messages), **kwargs})
        return self.reply

    def stream(self, messages, **kwargs):
        self.calls.append({"messages": list(messages), **kwargs})
        yield from (self.reply[i : i + 2] for i in range(0, len(self.reply), 2))

    async def achat(self, messages, **kwargs):
        self.calls.append({"messages": list(messages), **kwargs})
        return self.reply

    async def astream(self, messages, **kwargs):
        self.calls.append({"messages": list(messages), **kwargs})
        for i in range(0, len(self.reply), 2):
            yield self.reply[i : i + 2]


def test_send_appends_history():
    client = FakeClient("hello")
    chat = ChatEngine(client, system="be nice")
    reply = chat.send("hi")

    assert reply == "hello"
    assert chat.history == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    # system / thinking / effort are forwarded to the client.
    assert client.calls[0]["system"] == "be nice"


def test_multi_turn_accumulates():
    client = FakeClient("r")
    chat = ChatEngine(client)
    chat.send("one")
    chat.send("two")
    assert len(chat.history) == 4
    # The second call sees the full prior history.
    assert len(client.calls[1]["messages"]) == 3


def test_send_stream_accumulates_history():
    client = FakeClient("streamed")
    chat = ChatEngine(client)
    out = "".join(chat.send_stream("go"))
    assert out == "streamed"
    assert chat.history[-1] == {"role": "assistant", "content": "streamed"}


def test_reset():
    client = FakeClient()
    chat = ChatEngine(client)
    chat.send("x")
    chat.reset()
    assert chat.history == []


def test_max_history_trim():
    client = FakeClient("a")
    chat = ChatEngine(client, max_history=2)
    chat.send("1")
    chat.send("2")
    assert len(chat.history) == 2  # only the most recent two messages kept


def test_save_and_load(tmp_path):
    client = FakeClient("hi")
    chat = ChatEngine(client, system="persona")
    chat.send("hello")
    path = chat.save(tmp_path / "c.json")

    fresh = ChatEngine(FakeClient())
    fresh.load(path)
    assert fresh.system == "persona"
    assert fresh.history[0] == {"role": "user", "content": "hello"}


@pytest.mark.asyncio
async def test_async_send():
    client = FakeClient("async-ok")
    chat = ChatEngine(client)
    reply = await chat.asend("hi")
    assert reply == "async-ok"
    assert chat.history[-1]["content"] == "async-ok"


@pytest.mark.asyncio
async def test_async_stream():
    client = FakeClient("abcd")
    chat = ChatEngine(client)
    chunks = [c async for c in chat.asend_stream("go")]
    assert "".join(chunks) == "abcd"
    assert chat.history[-1]["content"] == "abcd"
