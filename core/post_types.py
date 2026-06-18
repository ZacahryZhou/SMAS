from __future__ import annotations

POST_TYPES = ("product_promo", "event_campaign", "general")

POST_TYPE_LABELS = {
    "product_promo": "商品推广",
    "event_campaign": "活动促销",
    "general": "通用",
}


def normalize_post_type(value: str) -> str:
    cleaned = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "product": "product_promo",
        "promo": "product_promo",
        "product_promotion": "product_promo",
        "event": "event_campaign",
        "campaign": "event_campaign",
        "event_promo": "event_campaign",
    }
    normalized = aliases.get(cleaned, cleaned)
    if normalized not in POST_TYPES:
        raise ValueError(f"Unsupported post_type: {value}")
    return normalized


def is_valid_post_type(value: str) -> bool:
    try:
        normalize_post_type(value)
        return True
    except ValueError:
        return False
