from __future__ import annotations

import json
from datetime import datetime, timezone

from core.brand_context import build_brand_context
from core.brief_binding import missing_brief_fields
from core.job_store import mark_step_done, read_json, write_json
from core.playbook import format_playbook_block, format_win_examples
from core.models import BrandProfile, CreativeBrief, VisualBrief
from core.post_types import POST_TYPE_LABELS
from core.profile_store import load_profile
from tools.deepseek_client import DeepSeekClient

SYSTEM_PROMPT = """
You are the Creative Brief Agent for SMAS.

Given a classified brief and brand profile, produce one creative brief that guides both caption and image generation.

Rules:
- headline: short post headline in brand account language when possible
- key_message: 1-2 sentence core message
- caption_angle: how the caption should feel and frame the post
- cta_hint: one engagement direction aligned with brand CTA style
- title and angle: short fields mirroring headline and caption_angle for downstream compatibility
- visual.scene: concrete Instagram image scene description in English
- visual.product_placement: where the product or focal subject should sit
- visual.composition: layout guidance such as rule of thirds, negative space
- visual.color_mood: tie to brand palette and post mood
- visual.text_on_image.enabled: true only for event_campaign or product_promo when short badges help
- visual.text_on_image.elements: 1-3 short uppercase labels max, never long sentences
- visual.use_user_assets: true only if assets_available is non-empty and post_type is product_promo
- visual.asset_roles: map asset filenames to roles like hero_product

Post-type guidance:
- product_promo: hero product, clean background, soft lifestyle context
- event_campaign: bold focal area, leave room for date/time overlay later, energetic mood
- general: atmospheric scene, minimal promo cues, usually no text on image

All fields below are required for downstream caption and image binding:
- headline, key_message, caption_angle, cta_hint must be non-empty
- visual.scene, visual.product_placement, visual.composition, visual.color_mood must be non-empty

Output valid json only:
{
  "headline": "...",
  "key_message": "...",
  "caption_angle": "...",
  "cta_hint": "...",
  "title": "...",
  "angle": "...",
  "visual": {
    "scene": "...",
    "product_placement": "...",
    "composition": "...",
    "color_mood": "...",
    "text_on_image": {
      "enabled": false,
      "elements": [],
      "style": ""
    },
    "use_user_assets": false,
    "asset_roles": {}
  }
}
""".strip()


def _build_system_prompt(post_type: str) -> str:
    parts = [SYSTEM_PROMPT]
    playbook_block = format_playbook_block(post_type)
    if playbook_block:
        parts.append(playbook_block)
    win_block = format_win_examples(post_type)
    if win_block:
        parts.append(win_block)
    return "\n\n".join(parts)


def sync_topic_from_brief(brief: CreativeBrief, *, user_request: str) -> dict:
    topic = {
        "mode": "guided",
        "user_request": user_request,
        "post_type": brief.post_type,
        "title": brief.title or brief.headline,
        "angle": brief.angle or brief.caption_angle,
        "content_type": "single_image",
        "reason": brief.key_message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json("topic.json", topic)
    return topic


class CreativeBriefAgent:
    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self._client = client or DeepSeekClient()

    def run(self, profile: BrandProfile | None = None) -> dict:
        profile = profile or load_profile()
        classification = read_json("brief.json")

        payload = {
            "classification": classification,
            "post_type": classification["post_type"],
            "post_type_label": classification.get("post_type_label")
            or POST_TYPE_LABELS.get(classification["post_type"], classification["post_type"]),
            "assets_available": classification.get("assets_available", []),
            "brand_context": build_brand_context(profile),
        }
        post_type = classification["post_type"]
        result = self._client.chat_json(
            system=_build_system_prompt(post_type),
            user=json.dumps(payload, ensure_ascii=False, indent=2),
            max_tokens=1536,
            temperature=0.4,
        )

        brief = CreativeBrief(
            post_type=classification["post_type"],
            user_request=classification.get("user_request", ""),
            headline=result.get("headline", ""),
            key_message=result.get("key_message", ""),
            caption_angle=result.get("caption_angle", ""),
            cta_hint=result.get("cta_hint", ""),
            title=result.get("title", result.get("headline", "")),
            angle=result.get("angle", result.get("caption_angle", "")),
            visual=VisualBrief.model_validate(result.get("visual", {})),
        )

        record = brief.model_dump()
        record["binding_gaps"] = missing_brief_fields(record)
        record["created_at"] = datetime.now(timezone.utc).isoformat()
        write_json("creative_brief.json", record)
        sync_topic_from_brief(brief, user_request=classification.get("user_request", ""))
        mark_step_done("brief", next_step="caption")
        return record
