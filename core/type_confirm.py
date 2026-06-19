from __future__ import annotations

from core.post_types import POST_TYPE_LABELS, POST_TYPES, normalize_post_type

CHOICE_MAP = {
    "1": "product_promo",
    "2": "event_campaign",
    "3": "general",
    "product_promo": "product_promo",
    "product promo": "product_promo",
    "promo": "product_promo",
    "product": "product_promo",
    "event_campaign": "event_campaign",
    "event campaign": "event_campaign",
    "event": "event_campaign",
    "campaign": "event_campaign",
    "general": "general",
}


def build_type_confirmation_prompt(brief: dict) -> str:
    guessed = brief.get("post_type", "general")
    confidence = brief.get("post_type_confidence", 0.0)
    reason = brief.get("reason", "")
    lines = [
        "Please confirm the post type before I generate content.",
        f"Guess: {POST_TYPE_LABELS.get(guessed, guessed)} (confidence {confidence:.0%})",
    ]
    if reason:
        lines.append(f"Reason: {reason}")
    lines.extend(
        [
            "",
            "Reply with a number or type name:",
            "1 / product promo — Product promo / 商品推广",
            "2 / event campaign — Event campaign / 活动促销",
            "3 / general — General / 通用",
            "",
            "Or: type: product promo",
        ]
    )
    return "\n".join(lines)


def parse_type_confirmation(text: str) -> str | None:
    cleaned = text.strip().lower()
    if not cleaned:
        return None

    if cleaned.startswith("type:"):
        cleaned = cleaned[len("type:") :].strip()

    if cleaned in CHOICE_MAP:
        return CHOICE_MAP[cleaned]

    for key, post_type in CHOICE_MAP.items():
        if len(key) > 1 and key in cleaned:
            return post_type

    try:
        return normalize_post_type(cleaned.replace(" ", "_"))
    except ValueError:
        return None
