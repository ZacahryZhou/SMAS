from __future__ import annotations

import json
from datetime import datetime, timezone

from core.asset_store import flatten_available_assets
from core.brand_context import build_brand_context
from core.job_store import mark_step_done, write_json
from core.models import BrandProfile, BriefClassification
from core.post_types import POST_TYPE_LABELS, POST_TYPES, normalize_post_type
from core.profile_store import load_profile
from core.request_parser import parse_requested_post_type, strip_render_prefix, strip_type_prefix
from tools.deepseek_client import DeepSeekClient

SYSTEM_PROMPT = """
You are the Content Classifier for SMAS, an Instagram content system.

Given a user request and brand profile, classify the post into exactly one post_type.

Allowed post_type values:
- product_promo: product promotion, selling points, new item showcase, soft conversion
- event_campaign: events, promotions, pop-up, limited-time offers, dates and places matter
- general: everyday updates, thoughts, brand presence without hard promo or event specifics

Rules:
- If user_specified_type is provided, use it unless it clearly contradicts the request.
- If assets_available is non-empty and the request mentions a product, prefer product_promo.
- If the request mentions dates, times, locations, RSVP, pop-up, sale window, use event_campaign.
- educational/tutorial requests should map to general for now.
- goal should be one of: awareness, conversion, engagement, event_signup, general_update
- Write user_intent and reason in the same language as the user request when possible.

Output valid json only:
{
  "post_type": "product_promo",
  "post_type_confidence": 0.0,
  "user_intent": "...",
  "goal": "conversion",
  "audience_focus": "...",
  "reason": "..."
}
""".strip()


class ContentClassifierAgent:
    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self._client = client or DeepSeekClient()

    def run(
        self,
        user_request: str,
        *,
        profile: BrandProfile | None = None,
        post_type: str | None = None,
    ) -> dict:
        profile = profile or load_profile()
        specified = post_type or parse_requested_post_type(user_request)
        cleaned_request = strip_render_prefix(strip_type_prefix(user_request))
        assets_available = flatten_available_assets()

        payload = {
            "user_request": cleaned_request,
            "user_specified_type": specified,
            "assets_available": assets_available,
            "allowed_post_types": list(POST_TYPES),
            "brand_context": build_brand_context(profile),
        }
        result = self._client.chat_json(
            system=SYSTEM_PROMPT,
            user=json.dumps(payload, ensure_ascii=False, indent=2),
            max_tokens=1024,
            temperature=0.2,
        )

        if specified:
            result["post_type"] = normalize_post_type(specified)
            result["post_type_confidence"] = max(float(result.get("post_type_confidence", 0.0)), 0.95)
        else:
            result["post_type"] = normalize_post_type(result["post_type"])

        brief = BriefClassification(
            post_type=result["post_type"],
            post_type_confidence=float(result.get("post_type_confidence", 0.0)),
            user_intent=result.get("user_intent", ""),
            goal=result.get("goal", ""),
            audience_focus=result.get("audience_focus", ""),
            reason=result.get("reason", ""),
            user_request=cleaned_request,
            assets_available=assets_available,
            user_specified_type=specified,
        )
        record = {
            **brief.model_dump(),
            "post_type_label": POST_TYPE_LABELS.get(brief.post_type, brief.post_type),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json("brief.json", record)
        mark_step_done("classify", next_step="brief")
        return record
