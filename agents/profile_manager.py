from __future__ import annotations

import json
from typing import Any

from core.brand_context import build_profile_summary
from core.models import BrandProfile, ProfileAgentResponse
from core.profile_store import apply_patch, load_profile
from tools.deepseek_client import DeepSeekClient

SYSTEM_PROMPT = """
You are the Profile Manager for SMAS, a social media content system.

Your job:
1. Help the user build or update their Instagram channel profile through conversation.
2. Ask focused follow-up questions when information is missing.
3. Return structured json that updates the profile incrementally.

Required onboarding information before setting onboarding_complete=true:
- account.display_name
- account.handle
- account.language
- niche.category
- niche.audience
- niche.positioning
- voice.tone (at least 1 item)
- visual.style_keywords (at least 1 item)

Behavior rules:
- Reply in the same language the user uses.
- Be concise and practical.
- If the user says "确认" / "confirm" / "done", only set onboarding_complete=true when required fields are present.
- If information is incomplete, keep onboarding_complete=false and ask the next best question.
- Never invent facts the user did not provide.
- For profile edits, only patch fields that should change.

Output json schema:
{
  "reply_to_user": "string",
  "patch": {
    "account": {"display_name": "...", "handle": "...", "language": "..."},
    "niche": {"category": "...", "audience": "...", "positioning": "..."},
    "voice": {"tone": ["..."], "avoid": ["..."], "cta_style": "..."},
    "visual": {"style_keywords": ["..."], "color_palette": ["..."], "no_text_on_image": true},
    "topic_sources": [{"type": "rss|reddit|manual", "enabled": true, "url": "...", "subreddit": "...", "weight": 1.0}],
    "onboarding_complete": false
  }
}

Only include keys inside patch that should change.
""".strip()


class ProfileManagerAgent:
    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self._client = client or DeepSeekClient()

    def handle_message(
        self,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> tuple[str, BrandProfile]:
        profile = load_profile()
        history = history or []

        user_payload = {
            "current_profile": profile.model_dump(),
            "conversation_history": history[-8:],
            "user_message": user_message,
        }

        raw = self._client.chat_json(
            system=SYSTEM_PROMPT,
            user=json.dumps(user_payload, ensure_ascii=False, indent=2),
            max_tokens=2048,
        )
        response = ProfileAgentResponse.model_validate(raw)

        patch: dict[str, Any] = dict(response.patch)
        if response.onboarding_complete is not None:
            patch["onboarding_complete"] = response.onboarding_complete

        updated = apply_patch(profile, patch)
        return response.reply_to_user, updated

    def start_onboarding(self) -> str:
        profile = load_profile()
        if profile.onboarding_complete:
            return (
                "你的品牌资料库已经建立完成。\n"
                f"{build_profile_summary(profile)}\n\n"
                "你可以直接描述想修改的内容，例如：\n"
                "「把风格改成更高级一点」"
            )

        reply, _ = self.handle_message(
            "你好，我想开始建立我的 Instagram 频道资料库。请开始问我问题。"
        )
        return reply
