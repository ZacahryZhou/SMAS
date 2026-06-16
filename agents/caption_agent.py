from __future__ import annotations

import json
from datetime import datetime, timezone

from core.brand_context import build_brand_context
from core.job_store import mark_step_done, read_json, write_json
from core.models import BrandProfile
from core.profile_store import load_profile
from tools.deepseek_client import DeepSeekClient

SYSTEM_PROMPT = """
You are the Caption Agent for SMAS, an Instagram content expert.

Given a topic and brand profile, write an Instagram caption.

Rules:
- Language must follow brand account language.
- hook: first line under 20 words, strong opener.
- body: 2-4 short bullet lines or compact paragraphs.
- cta: one engagement question, aligned with brand CTA style.
- hashtags: 8-15 relevant tags as an array of strings with leading #.
- alt_text: concise accessibility description for the image.
- Avoid advertisement tone and banned styles from brand profile.

Output valid json only:
{
  "hook": "...",
  "body": "...",
  "cta": "...",
  "hashtags": ["#TagOne", "#TagTwo"],
  "alt_text": "..."
}
""".strip()


def build_full_caption(hook: str, body: str, cta: str, hashtags: list[str]) -> str:
    tags = " ".join(hashtags)
    parts = [hook.strip(), "", body.strip(), "", cta.strip(), "", tags.strip()]
    return "\n".join(part for part in parts if part)


class CaptionAgent:
    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self._client = client or DeepSeekClient()

    def run(self, profile: BrandProfile | None = None) -> dict:
        profile = profile or load_profile()
        topic = read_json("topic.json")
        payload = {
            "topic": topic,
            "brand_context": build_brand_context(profile),
        }
        result = self._client.chat_json(
            system=SYSTEM_PROMPT,
            user=json.dumps(payload, ensure_ascii=False, indent=2),
            max_tokens=1536,
        )
        hashtags = result.get("hashtags", [])
        caption = {
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
