from __future__ import annotations

import json
from datetime import datetime, timezone

from core.brand_context import build_brand_context
from core.job_store import mark_step_done, write_json
from core.models import BrandProfile
from core.profile_store import load_profile
from tools.deepseek_client import DeepSeekClient

SYSTEM_PROMPT = """
You are the Topic Agent for SMAS, an Instagram content system.

Given a user request and brand profile, produce one strong post topic.

Rules:
- Match the brand category, audience, and positioning.
- Prefer practical, scroll-stopping angles for Instagram.
- Avoid hard-selling advertisement tone.
- content_type must be "single_image" for now.
- Write title and angle in the brand account language when possible.

Output valid json only:
{
  "mode": "guided",
  "title": "short post title",
  "angle": "how to frame the post",
  "content_type": "single_image",
  "reason": "why this fits the brand"
}
""".strip()


class TopicAgent:
    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self._client = client or DeepSeekClient()

    def run(self, user_request: str, profile: BrandProfile | None = None) -> dict:
        profile = profile or load_profile()
        payload = {
            "user_request": user_request,
            "brand_context": build_brand_context(profile),
        }
        result = self._client.chat_json(
            system=SYSTEM_PROMPT,
            user=json.dumps(payload, ensure_ascii=False, indent=2),
            max_tokens=1024,
        )
        topic = {
            "mode": "guided",
            "user_request": user_request,
            "title": result["title"],
            "angle": result["angle"],
            "content_type": result.get("content_type", "single_image"),
            "reason": result.get("reason", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json("topic.json", topic)
        mark_step_done("topic", next_step="caption")
        return topic
