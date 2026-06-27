"""Minimal streaming chat example.

Run with:  ANTHROPIC_API_KEY=sk-ant-... python examples/basic_chat.py
"""

from claude_crack import ChatEngine, ClaudeClient


def main() -> None:
    client = ClaudeClient(model="opus")
    chat = ChatEngine(client, system="You are a friendly, concise assistant.")

    for prompt in ("Hi! Who are you?", "Summarize what you just said in five words."):
        print(f"\nyou> {prompt}\nclaude> ", end="", flush=True)
        for delta in chat.send_stream(prompt):
            print(delta, end="", flush=True)
        print()

    client.close()


if __name__ == "__main__":
    main()
