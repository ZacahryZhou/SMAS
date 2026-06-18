from __future__ import annotations

import re

from core.post_types import normalize_post_type

_TYPE_PREFIX = re.compile(
    r"^(?:type|类型)\s*[:：]\s*(.+?)(?:[.。!！?？\n]|$)",
    re.IGNORECASE,
)

_TYPE_ALIASES: dict[str, str] = {
    # English
    "product promo": "product_promo",
    "product_promo": "product_promo",
    "product": "product_promo",
    "promo": "product_promo",
    "promotion": "product_promo",
    "event campaign": "event_campaign",
    "event_campaign": "event_campaign",
    "event": "event_campaign",
    "campaign": "event_campaign",
    "sale": "event_campaign",
    "general": "general",
    # Chinese
    "商品推广": "product_promo",
    "推广": "product_promo",
    "种草": "product_promo",
    "商品": "product_promo",
    "活动促销": "event_campaign",
    "活动": "event_campaign",
    "促销": "event_campaign",
    "通用": "general",
}


def parse_requested_post_type(user_request: str) -> str | None:
    match = _TYPE_PREFIX.search(user_request.strip())
    if not match:
        return None
    raw = match.group(1).strip().lower()
    for key, post_type in _TYPE_ALIASES.items():
        if key.lower() in raw or raw == key.lower():
            return post_type
    try:
        return normalize_post_type(raw)
    except ValueError:
        return None


def strip_type_prefix(user_request: str) -> str:
    return _TYPE_PREFIX.sub("", user_request, count=1).strip() or user_request.strip()


_RENDER_PREFIX = re.compile(
    r"(?:path|render|出图|路径)\s*[:：]\s*([ABCabc])\b",
    re.IGNORECASE,
)


def parse_render_path_override(user_request: str) -> str | None:
    match = _RENDER_PREFIX.search(user_request.strip())
    if not match:
        return None
    return match.group(1).upper()


def strip_render_prefix(user_request: str) -> str:
    return _RENDER_PREFIX.sub("", user_request, count=1).strip() or user_request.strip()
