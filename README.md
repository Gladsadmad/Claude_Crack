# Claude_Crack

**A small, cross-platform, embeddable client for Anthropic's Claude — built to drop cleanly into any Python app.**

`claude-crack` is a thin, opinionated layer over the official [`anthropic`](https://pypi.org/project/anthropic/) SDK. It clones the essential "talk to Claude" workflow into a few small, well-typed pieces and adds the options an application actually needs: cross-platform config, a stateful conversation engine, streaming, async, and a zero-dependency CLI.

It defaults to **`claude-opus-4-8`** with adaptive thinking, and chooses correct per-model settings (thinking mode, effort, output limits) for you.

---

## Why this exists

The raw SDK is great, but every app re-writes the same glue: where does the API key live, how do I store user defaults across Windows/macOS/Linux, how do I keep a multi-turn conversation, how do I stream tokens to a UI, how do I save/restore a session. `claude-crack` packages that glue so the integration is a few lines:

```python
from claude_crack import ClaudeClient, ChatEngine

client = ClaudeClient()                       # reads ANTHROPIC_API_KEY from the env
chat = ChatEngine(client, system="You are concise.")
print(chat.send("Give me a one-line summary of TCP."))
print(chat.send("And UDP?"))                  # remembers the previous turn
```

---

## Features

- **Cross-platform by design** — config lives in the right per-OS directory (`%APPDATA%`, `~/Library/Application Support`, `~/.config`) with no third-party path dependency.
- **Embeddable** — `ChatEngine` owns conversation state, system prompt, history trimming, and JSON save/restore so it sits naturally inside a GUI, web backend, or bot.
- **Sync *and* async** — every call has an `a`-prefixed async twin (`chat`/`achat`, `stream`/`astream`).
- **Streaming** — yield text deltas straight to a terminal or UI.
- **Sensible model defaults** — `claude-opus-4-8`, adaptive thinking, effort, and output caps picked per model from a built-in registry; aliases like `opus`/`sonnet`/`haiku`.
- **Clean errors** — SDK failures are normalized to `ClaudeCrackError` subclasses (including a dedicated `RefusalError`).
- **CLI included** — `claude-crack ask`, `claude-crack chat`, `claude-crack config`, `claude-crack models`.
- **Typed** — ships `py.typed`.

---

## Installation

```bash
pip install claude-crack
```

For the high-throughput async HTTP backend:

```bash
pip install "claude-crack[async]"
```

Set your key once:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."        # macOS/Linux
setx ANTHROPIC_API_KEY "sk-ant-..."          # Windows
```

---

## Library usage

### One-shot

```python
from claude_crack import ClaudeClient

client = ClaudeClient(model="opus")           # alias resolves to claude-opus-4-8
print(client.chat([{"role": "user", "content": "Hello!"}]))
```

### Streaming

```python
for delta in client.stream([{"role": "user", "content": "Write a haiku about Python."}]):
    print(delta, end="", flush=True)
```

### Stateful conversation

```python
from claude_crack import ClaudeClient, ChatEngine

chat = ChatEngine(ClaudeClient(), system="You are a helpful assistant.")
chat.send("My name is Chris.")
print(chat.send("What's my name?"))           # -> "Chris"

chat.save("session.json")                     # persist
chat.reset()
chat.load("session.json")                     # restore
```

### Async

```python
import asyncio
from claude_crack import ClaudeClient, ChatEngine

async def main():
    chat = ChatEngine(ClaudeClient())
    async for delta in chat.asend_stream("Tell me a joke."):
        print(delta, end="", flush=True)

asyncio.run(main())
```

### Thinking and effort

```python
client.chat(messages, thinking=True, effort="high")   # adaptive thinking, high effort
```

These are applied only to models that support them; older models silently skip them.

---

## CLI

```bash
claude-crack ask "What is the capital of France?"
claude-crack ask -s "Reply in French." "Describe Paris."
claude-crack chat                       # interactive REPL (/reset, /save, /exit)
claude-crack -m sonnet --thinking ask "Explain quantum tunneling simply."
claude-crack models                     # list known models
claude-crack config set model sonnet    # persist a default
claude-crack config show
```

Configuration is stored at `claude-crack config path`.

---

## Configuration

| Source (highest priority first) | Used for |
| --- | --- |
| Explicit `api_key=...` argument | API key |
| `Settings.api_key` (in-memory only) | API key |
| `CLAUDE_CRACK_API_KEY`, then `ANTHROPIC_API_KEY` env vars | API key |
| `Settings` file (`config path`) | model, system prompt, thinking, effort, max_tokens |

The API key is **never** written to the settings file — keep secrets in the environment or your app's secret store.

---

## Public API

| Symbol | Purpose |
| --- | --- |
| `ClaudeClient` | Sync/async client wrapper (`chat`, `stream`, `achat`, `astream`, `list_models`) |
| `ChatEngine` | Stateful multi-turn conversation manager with save/restore |
| `Settings` | Cross-platform settings (`load`, `save`) |
| `config_dir`, `config_path`, `resolve_api_key` | Config helpers |
| `known_models`, `get_model_info`, `resolve_model`, `DEFAULT_MODEL` | Model registry |
| `ClaudeCrackError`, `ConfigError`, `APIKeyMissingError`, `ClaudeAPIError`, `RefusalError` | Exceptions |

---

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

The test suite stubs the network, so no API key is required to run it.

---

## License

[MIT](LICENSE) © Christopher S. Day
