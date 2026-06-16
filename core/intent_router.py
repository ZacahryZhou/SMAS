from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core.job_store import try_read_json


@dataclass
class RoutedIntent:
    intent: str
    payload: dict[str, Any]


GENERATE_PATTERNS = (
    r"做一条",
    r"生成",
    r"发帖",
    r"create a post",
    r"generate",
    r"make a post",
)

PROFILE_PATTERNS = (
    r"风格",
    r"资料",
    r"账号",
    r"profile",
    r"数据源",
)

APPROVE_PATTERNS = (r"^ok$", r"^yes$", r"发布", r"approve", r"确认")
SKIP_PATTERNS = (r"^skip$", r"跳过", r"cancel", r"取消")


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = text.strip().lower()
    for pattern in patterns:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return True
    return False


def route_message(text: str) -> RoutedIntent:
    cleaned = text.strip()
    if not cleaned:
        return RoutedIntent("unknown", {})

    state = try_read_json("state.json")
    if state and state.get("status") == "waiting_review":
        if _matches_any(cleaned, APPROVE_PATTERNS):
            return RoutedIntent("review_action", {"action": "approve"})
        if _matches_any(cleaned, SKIP_PATTERNS):
            return RoutedIntent("review_action", {"action": "skip"})

    if cleaned.startswith("/generate "):
        return RoutedIntent(
            "generate_content",
            {"user_request": cleaned[len("/generate ") :].strip()},
        )

    if _matches_any(cleaned, GENERATE_PATTERNS):
        return RoutedIntent("generate_content", {"user_request": cleaned})

    if cleaned.startswith("/profile") or _matches_any(cleaned, PROFILE_PATTERNS):
        return RoutedIntent("manage_profile", {"message": cleaned})

    if cleaned in {"/status", "status", "状态"}:
        return RoutedIntent("query_status", {})

    if cleaned in {"/help", "help", "帮助"}:
        return RoutedIntent("help", {})

    if cleaned in {"/start", "start"}:
        return RoutedIntent("start", {})

    return RoutedIntent("unknown", {"message": cleaned})
