#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.orchestrator import Orchestrator  # noqa: E402


def cmd_generate(request: str) -> int:
    result = Orchestrator().generate(request)
    payload = {
        "ok": True,
        "text": result.text,
        "preview_image": str(result.image_path) if result.image_path else None,
        "caption_file": str(ROOT / "state" / "caption.json"),
        "state_file": str(ROOT / "state" / "state.json"),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_message(text: str) -> int:
    result = Orchestrator().handle_text(text)
    payload = {
        "ok": True,
        "text": result.text,
        "preview_image": str(result.image_path) if result.image_path else None,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SMAS helper for OpenClaw")
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate")
    generate.add_argument("request")

    message = sub.add_parser("message")
    message.add_argument("text")

    args = parser.parse_args()
    if args.command == "generate":
        return cmd_generate(args.request)
    return cmd_message(args.text)


if __name__ == "__main__":
    raise SystemExit(main())
