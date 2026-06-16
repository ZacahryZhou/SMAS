from __future__ import annotations

import argparse
import sys

from config import ensure_dirs, settings
from core.brand_context import build_profile_summary
from core.profile_store import load_profile, reset_profile


def cmd_check() -> int:
    print("SMAS API check")
    print(f"- DRY_RUN: {settings.dry_run}")

    if not settings.deepseek_api_key:
        print("- DeepSeek: MISSING (set DEEPSEEK_API_KEY in .env)")
        return 1

    try:
        from tools.deepseek_client import ping

        reply = ping()
        print(f"- DeepSeek: OK ({reply})")
    except Exception as exc:
        print(f"- DeepSeek: FAILED ({exc})")
        return 1

    if settings.fal_key:
        print("- fal.ai: key present (image test happens in M2)")
    else:
        print("- fal.ai: key not set yet (needed in M2, not required for M1)")

    return 0


def cmd_profile_show() -> int:
    profile = load_profile()
    print(build_profile_summary(profile))
    return 0


def cmd_profile_reset() -> int:
    reset_profile()
    print("品牌资料库已重置。")
    return 0


def cmd_profile_chat(message: str) -> int:
    from agents.profile_manager import ProfileManagerAgent

    agent = ProfileManagerAgent()
    reply, profile = agent.handle_message(message)
    print("\n助手:")
    print(reply)
    print("\n---")
    print(build_profile_summary(profile))
    return 0


def cmd_profile_interactive() -> int:
    from agents.profile_manager import ProfileManagerAgent

    agent = ProfileManagerAgent()
    print(agent.start_onboarding())
    print("\n输入内容继续建档或修改。输入 exit 退出。\n")

    history: list[dict[str, str]] = []
    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            return 0

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q", "退出"}:
            print("已退出。")
            return 0

        reply, profile = agent.handle_message(user_input, history=history)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})

        print("\n助手:")
        print(reply)
        print("\n---")
        print(build_profile_summary(profile))
        print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SMAS - Social Media Agent System")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check", help="Check API configuration")

    profile_parser = sub.add_parser("profile", help="Manage brand profile")
    profile_parser.add_argument(
        "action",
        nargs="?",
        choices=["show", "reset", "chat"],
        help="Profile action",
    )
    profile_parser.add_argument("message", nargs="?", help="Single chat message for profile chat")

    return parser


def main(argv: list[str] | None = None) -> int:
    ensure_dirs()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check":
        return cmd_check()

    if args.command == "profile":
        if args.action == "show":
            return cmd_profile_show()
        if args.action == "reset":
            return cmd_profile_reset()
        if args.action == "chat":
            if not args.message:
                print("Usage: python main.py profile chat \"你的消息\"")
                return 1
            return cmd_profile_chat(args.message)
        return cmd_profile_interactive()

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
