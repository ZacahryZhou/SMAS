from __future__ import annotations

import re
from dataclasses import dataclass, field

_EDIT_PREFIX = re.compile(r"^(?:edit|修改|改)\s*[:：]\s*", re.IGNORECASE)

_PATH_PATTERN = re.compile(
    r"(?:路径|path|render|出图)\s*[:：]?\s*([ABCabc])\b|换成\s*(?:path\s*)?([ABCabc])\b",
    re.IGNORECASE,
)

_CAPTION_PREFIX = re.compile(r"^(?:改文案|文案|caption|hook)\s*[:：]\s*", re.IGNORECASE)

_IMAGE_KEYWORDS = (
    r"字大",
    r"字小",
    r"bigger",
    r"smaller",
    r"商品",
    r"product",
    r"路径",
    r"path",
    r"出图",
    r"背景",
    r"图片",
    r"image",
    r"overlay",
    r"叠字",
)

_CAPTION_KEYWORDS = (
    r"文案",
    r"caption",
    r"hook",
    r"hashtag",
    r"标签",
    r"cta",
    r"语气",
    r"tone",
)


@dataclass
class EditRequest:
    raw_instruction: str = ""
    caption_note: str = ""
    path_override: str | None = None
    product_shift: tuple[float, float] | None = None
    text_size_delta: int = 0
    overlay_text: str | None = None
    scopes: list[str] = field(default_factory=list)


def normalize_edit_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = _EDIT_PREFIX.sub("", cleaned).strip()
    return cleaned or text.strip()


def is_edit_message(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    if _EDIT_PREFIX.search(cleaned):
        return True
    lowered = cleaned.lower()
    if _CAPTION_PREFIX.search(cleaned):
        return True
    if _PATH_PATTERN.search(cleaned):
        return True
    for pattern in _IMAGE_KEYWORDS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return True
    for pattern in _CAPTION_KEYWORDS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return True
    return False


def _clamp(value: float, low: float = 0.12, high: float = 0.88) -> float:
    return max(low, min(high, value))


def parse_edit_instruction(text: str) -> EditRequest:
    raw = normalize_edit_text(text)
    edit = EditRequest(raw_instruction=raw)
    lowered = raw.lower()

    path_match = _PATH_PATTERN.search(raw)
    if path_match:
        letter = (path_match.group(1) or path_match.group(2) or "").upper()
        if letter in {"A", "B", "C"}:
            edit.path_override = letter

    if re.search(r"字大一点|字大点|大一点|bigger text|larger text", lowered):
        edit.text_size_delta = 1
    elif re.search(r"字小一点|字小点|小一点|smaller text", lowered):
        edit.text_size_delta = -1

    if re.search(r"商品往右|商品右移|product right|move right", lowered):
        edit.product_shift = (0.08, 0.0)
    elif re.search(r"商品往左|商品左移|product left|move left", lowered):
        edit.product_shift = (-0.08, 0.0)
    elif re.search(r"商品往上|product up|move up", lowered):
        edit.product_shift = (0.0, -0.08)
    elif re.search(r"商品往下|product down|move down", lowered):
        edit.product_shift = (0.0, 0.08)

    caption_match = _CAPTION_PREFIX.match(raw)
    if caption_match:
        edit.caption_note = raw[caption_match.end() :].strip()
    elif re.search(r"改文案|rewrite caption|change caption", lowered):
        edit.caption_note = re.sub(
            r"^(?:改文案|rewrite caption|change caption)\s*[:：]?\s*",
            "",
            raw,
            flags=re.IGNORECASE,
        ).strip()

    overlay_match = re.search(r"(?:叠字|标题|overlay|badge)\s*[:：]\s*(.+)$", raw, flags=re.IGNORECASE)
    if overlay_match:
        edit.overlay_text = overlay_match.group(1).strip().strip("'\"")

    edit.scopes = infer_scopes(edit)
    return edit


def infer_scopes(edit: EditRequest) -> list[str]:
    scopes: list[str] = []
    lowered = edit.raw_instruction.lower()

    wants_image = any(
        [
            edit.path_override,
            edit.product_shift,
            edit.text_size_delta,
            edit.overlay_text,
            any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in _IMAGE_KEYWORDS),
        ]
    )
    wants_caption = bool(edit.caption_note) or any(
        re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in _CAPTION_KEYWORDS
    )

    if wants_image:
        scopes.append("image")
    if wants_caption:
        scopes.append("caption")

    if not scopes:
        if edit.raw_instruction:
            scopes.append("caption")
        else:
            scopes.append("image")
    return scopes
