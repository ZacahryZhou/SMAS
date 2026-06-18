# 这个文件是意图转换器，可以把用户发的一段自然语言文字，翻译成系统能够理解的标签意图
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core.edit_parser import is_edit_message, normalize_edit_text
from core.job_store import try_read_json


@dataclass
class RoutedIntent:
    intent: str
    payload: dict[str, Any]

# 上面的意思就是用户的意图和附带的参数，比如测试的时候用户说要做一条关于什么什么的帖子

# because in the real situation, the user will talk to the ai what they want
# and this file will translate the user's natural language into a tag intent
# so that the orchestrator can understand the user's intent and take appropriate action

# therefore this part is about the 意图识别
GENERATE_PATTERNS = (
    # English
    r"create a post",
    r"generate",
    r"make a post",
    r"create post",
    r"write a post",
    r"post about",
    # Chinese
    r"做一条",
    r"生成",
    r"发帖",
)

PROFILE_PATTERNS = (
    # English
    r"profile",
    r"brand profile",
    r"style",
    r"account",
    r"data source",
    # Chinese
    r"风格",
    r"资料",
    r"账号",
    r"数据源",
)

APPROVE_PATTERNS = (
    r"^ok$",
    r"^yes$",
    r"publish",
    r"approve",
    r"confirm",
    r"发布",
    r"确认",
)

SKIP_PATTERNS = (
    r"^skip$",
    r"cancel",
    r"discard",
    r"drop",
    r"跳过",
    r"取消",
)


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
        if cleaned.lower().startswith("/edit "):
            return RoutedIntent("review_edit", {"instruction": cleaned[len("/edit ") :].strip()})
        if is_edit_message(cleaned):
            return RoutedIntent("review_edit", {"instruction": normalize_edit_text(cleaned)})

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
