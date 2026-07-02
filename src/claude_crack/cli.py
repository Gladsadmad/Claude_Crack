"""Command-line interface for claude-crack.

Provides a cross-platform terminal app on top of the library:

    claude-crack ask "What is the capital of France?"
    claude-crack chat                 # interactive REPL
    claude-crack models               # list known models
    claude-crack config show          # inspect persisted settings

Built on argparse only — no extra dependencies, identical behavior on
Windows, macOS, and Linux.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import __version__, models
from .client import ClaudeClient
from .config import Settings, config_path
from .conversation import ChatEngine
from .exceptions import ClaudeCrackError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claude-crack",
        description="A cross-platform, embeddable client for Claude.",
    )
    parser.add_argument("--version", action="version", version=f"claude-crack {__version__}")
    parser.add_argument("-m", "--model", help="Model ID or alias (e.g. opus, sonnet, haiku).")
    parser.add_argument("--thinking", action="store_true", help="Enable adaptive thinking.")
    parser.add_argument(
        "--effort",
        choices=["low", "medium", "high", "max"],
        help="Effort level for supporting models.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_ask = sub.add_parser("ask", help="Send a single prompt and print the reply.")
    p_ask.add_argument("prompt", nargs="+", help="The prompt text.")
    p_ask.add_argument("-s", "--system", help="System prompt.")
    p_ask.add_argument(
        "--no-stream", action="store_true", help="Wait for the full reply instead of streaming."
    )

    p_chat = sub.add_parser("chat", help="Start an interactive chat session.")
    p_chat.add_argument("-s", "--system", help="System prompt for the session.")

    sub.add_parser("models", help="List known Claude models.")

    p_cfg = sub.add_parser("config", help="Inspect or edit persisted settings.")
    cfg_sub = p_cfg.add_subparsers(dest="config_command", required=True)
    cfg_sub.add_parser("show", help="Print current settings.")
    cfg_sub.add_parser("path", help="Print the settings file path.")
    p_set = cfg_sub.add_parser("set", help="Set a setting (model, system_prompt, effort, ...).")
    p_set.add_argument("key")
    p_set.add_argument("value")

    return parser


def _cmd_models() -> int:
    for info in models.known_models():
        print(
            f"{info.id:<22} {info.display_name:<20} "
            f"ctx={info.context_window:>9,}  out={info.max_output:>7,}"
        )
    return 0


def _cmd_config(args: argparse.Namespace) -> int:
    if args.config_command == "path":
        print(config_path())
        return 0

    settings = Settings.load()
    if args.config_command == "show":
        for field_name in ("model", "system_prompt", "max_tokens", "thinking", "effort"):
            print(f"{field_name} = {getattr(settings, field_name)!r}")
        return 0

    if args.config_command == "set":
        key, value = args.key, args.value
        if not hasattr(settings, key) or key in ("api_key", "extra"):
            print(f"Unknown or unsettable key: {key}", file=sys.stderr)
            return 2
        # Coerce simple types based on the existing default.
        current = getattr(settings, key)
        coerced: object
        if isinstance(current, bool):
            coerced = value.lower() in ("1", "true", "yes", "on")
        elif isinstance(current, int):
            coerced = int(value)
        else:
            coerced = value
        setattr(settings, key, coerced)
        path = settings.save()
        print(f"Set {key} = {coerced!r} (saved to {path})")
        return 0

    return 2


def _make_client(args: argparse.Namespace, settings: Settings) -> ClaudeClient:
    return ClaudeClient(model=args.model or settings.model, settings=settings)


def _cmd_ask(args: argparse.Namespace, settings: Settings) -> int:
    prompt = " ".join(args.prompt)
    client = _make_client(args, settings)
    engine = ChatEngine(
        client,
        system=args.system or settings.system_prompt,
        thinking=args.thinking or None,
        effort=args.effort,
    )
    try:
        if args.no_stream:
            print(engine.send(prompt))
        else:
            for delta in engine.send_stream(prompt):
                sys.stdout.write(delta)
                sys.stdout.flush()
            print()
    finally:
        client.close()
    return 0


def _cmd_chat(args: argparse.Namespace, settings: Settings) -> int:
    client = _make_client(args, settings)
    engine = ChatEngine(
        client,
        system=args.system or settings.system_prompt,
        thinking=args.thinking or None,
        effort=args.effort,
    )
    print(f"claude-crack {__version__} — model: {client.model}")
    print("Type your message. Commands: /reset, /save <file>, /exit\n")
    try:
        while True:
            try:
                line = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            if line in ("/exit", "/quit"):
                break
            if line == "/reset":
                engine.reset()
                print("(conversation cleared)")
                continue
            if line.startswith("/save"):
                parts = line.split(maxsplit=1)
                target = parts[1] if len(parts) > 1 else "conversation.json"
                print(f"(saved to {engine.save(target)})")
                continue
            sys.stdout.write("claude> ")
            sys.stdout.flush()
            for delta in engine.send_stream(line):
                sys.stdout.write(delta)
                sys.stdout.flush()
            print("\n")
    finally:
        client.close()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``claude-crack`` console script."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "models":
            return _cmd_models()
        if args.command == "config":
            return _cmd_config(args)

        settings = Settings.load()
        if args.command == "ask":
            return _cmd_ask(args, settings)
        if args.command == "chat":
            return _cmd_chat(args, settings)
    except ClaudeCrackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.error("unknown command")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
