"""Example: embedding ChatEngine inside an application class.

This sketches how a host app (GUI, web backend, bot) would wrap claude-crack:
one client, one engine per user/session, persisted to disk between runs.

Run with:  ANTHROPIC_API_KEY=sk-ant-... python examples/embed_in_app.py
"""

from __future__ import annotations

from pathlib import Path

from claude_crack import ChatEngine, ClaudeClient, Settings, config_dir


class Assistant:
    """A tiny app-facing wrapper around a single conversation."""

    def __init__(self, persona: str) -> None:
        # Load persisted user defaults (model, effort, ...) from the OS config dir.
        settings = Settings.load()
        self.client = ClaudeClient(settings=settings)
        self.engine = ChatEngine(
            self.client,
            system=persona,
            max_history=40,  # cap memory for a long-running embedded session
        )
        self.session_file = config_dir() / "last_session.json"
        if self.session_file.exists():
            self.engine.load(self.session_file)

    def ask(self, message: str) -> str:
        reply = self.engine.send(message)
        self.engine.save(self.session_file)  # persist after each turn
        return reply

    def shutdown(self) -> None:
        self.client.close()


def main() -> None:
    assistant = Assistant(persona="You are the in-app help assistant for a photo editor.")
    print(assistant.ask("How do I crop an image?"))
    print(f"\n(session saved to {Path(assistant.session_file)})")
    assistant.shutdown()


if __name__ == "__main__":
    main()
