from __future__ import annotations

import json
from datetime import datetime, timezone

from core.brand_context import build_brand_context
from core.job_store import mark_step_done, read_json, write_json
from core.models import BrandProfile
from core.post_types import POST_TYPE_LABELS
from core.profile_store import load_profile
from tools.deepseek_client import DeepSeekClient

BASE_RULES = """
Rules:
- Language must follow brand account language.
- hook: first line under 20 words, strong opener.
- cta: one engagement line aligned with brand CTA style and cta_hint.
- hashtags: 8-15 relevant tags as an array of strings with leading #.
- alt_text: concise accessibility description for the image.
- Avoid advertisement tone and banned styles from brand profile.
"""

PROMPTS = {
    "product_promo": f"""
You are the Caption Agent for SMAS writing a product_promo Instagram caption.

Structure:
- hook: scroll-stopping opener tied to the product benefit
- body: exactly 3 short bullet lines, each one clear selling point
- cta: soft question or comment prompt, not hard sell

{BASE_RULES}

Output valid json only:
{{
  "hook": "...",
  "body": "- point one\\n- point two\\n- point three",
  "cta": "...",
  "hashtags": ["#TagOne"],
  "alt_text": "..."
}}
""".strip(),
    "event_campaign": f"""
You are the Caption Agent for SMAS writing an event_campaign Instagram caption.

Structure:
- hook: lead with the main benefit or excitement of the event
- body: include time, place, and key rules or details in compact lines
- cta: clear urgency to comment, save, or RSVP depending on brand style

{BASE_RULES}

Output valid json only:
{{
  "hook": "...",
  "body": "...",
  "cta": "...",
  "hashtags": ["#TagOne"],
  "alt_text": "..."
}}
""".strip(),
    "general": f"""
You are the Caption Agent for SMAS writing a general Instagram caption.

Structure:
- hook: first line under 20 words, strong opener
- body: 2-4 short bullet lines or compact paragraphs
- cta: one engagement question aligned with brand CTA style

{BASE_RULES}

Output valid json only:
{{
  "hook": "...",
  "body": "...",
  "cta": "...",
  "hashtags": ["#TagOne"],
  "alt_text": "..."
}}
""".strip(),
}


def build_full_caption(hook: str, body: str, cta: str, hashtags: list[str]) -> str:
    tags = " ".join(hashtags)
    parts = [hook.strip(), "", body.strip(), "", cta.strip(), "", tags.strip()]
    return "\n".join(part for part in parts if part)


def _load_brief_context() -> dict:
    try:
        return read_json("creative_brief.json")
    except FileNotFoundError:
        topic = read_json("topic.json")
        return {
            "post_type": topic.get("post_type", "general"),
            "headline": topic.get("title", ""),
            "key_message": topic.get("reason", ""),
            "caption_angle": topic.get("angle", ""),
            "cta_hint": "",
            "visual": {},
        }


class CaptionAgent:
    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self._client = client or DeepSeekClient()

    def run(self, profile: BrandProfile | None = None, *, edit_instruction: str | None = None) -> dict:
        profile = profile or load_profile()
        brief = _load_brief_context()
        post_type = brief.get("post_type", "general")
        system_prompt = PROMPTS.get(post_type, PROMPTS["general"])
        if edit_instruction:
            system_prompt += (
                "\n\nThe user wants to revise the current caption. "
                "Apply edit_instruction while keeping the same post_type structure and brand voice."
            )

        payload = {
            "creative_brief": brief,
            "post_type": post_type,
            "post_type_label": POST_TYPE_LABELS.get(post_type, post_type),
            "brand_context": build_brand_context(profile),
        }
        if edit_instruction:
            payload["current_caption"] = read_json("caption.json")
            payload["edit_instruction"] = edit_instruction
        result = self._client.chat_json(
            system=system_prompt,
            user=json.dumps(payload, ensure_ascii=False, indent=2),
            max_tokens=1536,
        )
        hashtags = result.get("hashtags", [])
        caption = {
            "post_type": post_type,
            "hook": result["hook"],
            "body": result["body"],
            "cta": result["cta"],
            "hashtags": hashtags,
            "alt_text": result.get("alt_text", ""),
            "full_caption": build_full_caption(
                result["hook"],
                result["body"],
                result["cta"],
                hashtags,
            ),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json("caption.json", caption)
        mark_step_done("caption", next_step="image")
        return caption
