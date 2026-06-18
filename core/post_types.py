from __future__ import annotations

POST_TYPES = ("product_promo", "event_campaign", "general")

POST_TYPE_LABELS: dict[str, str] = {
    "product_promo": "Product promo",
    "event_campaign": "Event campaign",
    "general": "General",
}


def normalize_post_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in POST_TYPES:
        return normalized
    raise ValueError(f"Unsupported post_type: {value}")
