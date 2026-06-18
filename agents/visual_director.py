#这个文件是还在读取brief和caption 调用DeepSeek的AP AI 然后决定使用哪条path以及具体的视觉参数 输出visual_spec.json

from __future__ import annotations

import json
from datetime import datetime, timezone

from config import settings
from core.asset_manager import pick_default_product
from core.brand_context import build_brand_context
from core.job_store import mark_step_done, read_json, write_json
from core.models import (
    AssetUsed,
    BrandProfile,
    ColorSpec,
    CompositionSpec,
    TextOverlayLine,
    TextOverlaySpec,
    VisualSpec,
)
from core.profile_store import load_profile
from core.request_parser import parse_render_path_override
from tools.deepseek_client import DeepSeekClient


#这个system prompt 是给视觉导演的指令
#1-> how to write the system prompt: -> give a ai role + define input/output format
#2-> how to design decision logic -> when to use different path and why
#3-> how to connect the LangGraph -> the run() function is a natura; LangGraph node 



SYSTEM_PROMPT = """
You are the Visual Director for SMAS.

Given creative brief, caption, brand profile, and a recommended render path, produce a visual_spec for image rendering.

Allowed path values: A, B, C
- Path A: pure AI text-to-image scene, no user product asset
- Path B: fal edit with product reference image placed in a lifestyle scene
- Path C: template composite with Pillow text overlays and optional product cutout

Rules:
- path should match recommended_path unless you have a strong documented reason
- path_b_edit_prompt: English prompt for Path B only; describe scene around the reference product
- path_a_prompt: English prompt for Path A only; scene-led, no text in image
- For Path C: text_overlay lines 1-3 short labels; assets_used for hero_product
- For Path B: assets_used must include hero_product; text_overlay.enabled should be false
- event_campaign: path C with text_overlay enabled
- product_promo with assets: path B for lifestyle scene, path C for badge/price labels

Output valid json only:
{
  "path": "B",
  "path_reason": "...",
  "composition": {
    "layout": "hero_center",
    "product_position": [0.55, 0.5],
    "text_safe_zones": ["top-left"]
  },
  "color": {
    "background": "#F5F0EB",
    "accent": "#E85D4C",
    "mood": "..."
  },
  "text_overlay": {
    "enabled": false,
    "lines": []
  },
  "assets_used": [
    {"path": "assets/products/item.png", "role": "hero_product", "needs_cutout": false}
  ],
  "path_a_prompt": "...",
  "path_b_edit_prompt": "...",
  "path_c_template": "product_hero_v1",
  "path_c_use_ai_background": false
}
""".strip()


def decide_default_path(
    *,
    post_type: str,
    assets_available: list[str],
    visual: dict,
    render_override: str | None = None,
) -> tuple[str, str]:
    if render_override in {"A", "B", "C"}:
        return render_override, f"user requested Path {render_override}"

    if post_type == "event_campaign":
        return "C", "event_campaign requires reliable text overlay via template"

    if post_type == "product_promo" and assets_available and visual.get("use_user_assets", True):
        text_on_image = visual.get("text_on_image", {})
        mode = settings.product_render_path

        if mode == "c":
            return "C", "product template composite (SMAS_PRODUCT_RENDER_PATH=c)"
        if mode == "b":
            return "B", "product reference scene generation (SMAS_PRODUCT_RENDER_PATH=b)"

        if text_on_image.get("enabled"):
            return "C", "product promo with on-image labels needs template overlay"
        return "B", "product asset available for reference scene generation"

    return "A", "default AI scene generation"


def _default_colors(profile: BrandProfile) -> ColorSpec:
    background = "#F5F0EB"
    accent = "#E85D4C"
    if profile.visual.color_palette:
        background = profile.visual.color_palette[0]
        if len(profile.visual.color_palette) > 1:
            accent = profile.visual.color_palette[1]
    return ColorSpec(background=background, accent=accent, mood=", ".join(profile.visual.style_keywords))


def _overlay_from_brief(creative_brief: dict, post_type: str) -> TextOverlaySpec:
    visual = creative_brief.get("visual", {})
    text_on_image = visual.get("text_on_image", {})
    if not text_on_image.get("enabled") and post_type != "event_campaign":
        return TextOverlaySpec(enabled=False, lines=[])

    lines: list[TextOverlayLine] = []
    elements = text_on_image.get("elements") or []
    zones = ["top-left", "bottom-center", "top-center"]
    sizes = ["large", "medium", "small"]
    for index, text in enumerate(elements[:3]):
        if not str(text).strip():
            continue
        lines.append(
            TextOverlayLine(
                text=str(text).strip().upper(),
                zone=zones[min(index, len(zones) - 1)],
                size=sizes[min(index, len(sizes) - 1)],
            )
        )

    if not lines and post_type == "event_campaign":
        headline = creative_brief.get("headline") or creative_brief.get("title") or "EVENT"
        detail = creative_brief.get("key_message", "")
        lines.append(TextOverlayLine(text=headline[:32].upper(), zone="top-left", size="large"))
        if detail:
            lines.append(TextOverlayLine(text=detail[:40], zone="bottom-center", size="medium"))

    return TextOverlaySpec(enabled=bool(lines), lines=lines)


def _default_assets(creative_brief: dict, assets_available: list[str], path: str) -> list[AssetUsed]:
    if path not in {"B", "C"}:
        return []

    visual = creative_brief.get("visual", {})
    roles = visual.get("asset_roles") or {}
    assets: list[AssetUsed] = []
    for rel_path, role in roles.items():
        if rel_path in assets_available:
            full_path = rel_path
        elif rel_path.startswith("assets/"):
            full_path = rel_path if rel_path in assets_available else rel_path
        else:
            full_path = next(
                (asset for asset in assets_available if asset.endswith(f"/{rel_path}") or asset.endswith(rel_path)),
                f"assets/products/{rel_path}",
            )
        if full_path in assets_available:
            assets.append(
                AssetUsed(
                    path=full_path,
                    role=role,
                    needs_cutout=path == "C",
                )
            )

    if assets:
        return assets

    default_product = pick_default_product(assets_available)
    if default_product and creative_brief.get("post_type") == "product_promo":
        return [
            AssetUsed(
                path=default_product,
                role="hero_product",
                needs_cutout=path == "C",
            )
        ]
    return []


def _default_path_b_prompt(creative_brief: dict) -> str:
    visual = creative_brief.get("visual", {})
    scene = visual.get("scene") or "clean lifestyle instagram scene"
    placement = visual.get("product_placement") or "hero product in scene"
    mood = visual.get("color_mood") or "warm natural light"
    return (
        f"Place the reference product in {scene}. {placement}. {mood}. "
        "Instagram vertical photo, realistic, clean composition, no text, no words, no typography."
    )


def _apply_path_rules(
    spec: VisualSpec,
    *,
    recommended_path: str,
    post_type: str,
    assets_available: list[str],
    creative_brief: dict,
    profile: BrandProfile,
) -> VisualSpec:
    spec.path = recommended_path
    spec.post_type = post_type

    if recommended_path in {"B", "C"} and not spec.assets_used:
        spec.assets_used = _default_assets(creative_brief, assets_available, recommended_path)

    if recommended_path == "C":
        if not spec.text_overlay.enabled or not spec.text_overlay.lines:
            spec.text_overlay = _overlay_from_brief(creative_brief, post_type)
        if not spec.color.background:
            spec.color = _default_colors(profile)
        if post_type == "event_campaign":
            spec.path_c_template = "event_hero_v1"
        elif post_type == "product_promo":
            spec.path_c_template = "product_hero_v1"

    if recommended_path == "B":
        spec.text_overlay = TextOverlaySpec(enabled=False, lines=[])
        if not spec.path_b_edit_prompt:
            spec.path_b_edit_prompt = _default_path_b_prompt(creative_brief)
        if not spec.assets_used:
            spec.path = "A"
            spec.path_reason = "Path B requested but no product asset found; falling back to Path A"

    if recommended_path == "A" and not spec.path_a_prompt:
        visual = creative_brief.get("visual", {})
        scene = visual.get("scene") or creative_brief.get("headline") or "clean instagram lifestyle scene"
        spec.path_a_prompt = (
            f"{scene}, {visual.get('color_mood', '')}, instagram vertical 4:5, "
            "clean composition, no text, no words, no typography, no logo"
        ).strip(", ")

    return spec


class VisualDirectorAgent:
    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self._client = client or DeepSeekClient()

    def run(self, profile: BrandProfile | None = None) -> dict:
        profile = profile or load_profile()
        creative_brief = read_json("creative_brief.json")
        classification = read_json("brief.json")
        caption = read_json("caption.json")

        post_type = creative_brief.get("post_type", "general")
        assets_available = classification.get("assets_available", [])
        visual = creative_brief.get("visual", {})
        user_request = classification.get("user_request", creative_brief.get("user_request", ""))
        render_override = parse_render_path_override(user_request)

        recommended_path, recommended_reason = decide_default_path(
            post_type=post_type,
            assets_available=assets_available,
            visual=visual,
            render_override=render_override,
        )

        payload = {
            "creative_brief": creative_brief,
            "caption": caption,
            "recommended_path": recommended_path,
            "recommended_reason": recommended_reason,
            "render_override": render_override,
            "assets_available": assets_available,
            "brand_context": build_brand_context(profile),
        }
        result = self._client.chat_json(
            system=SYSTEM_PROMPT,
            user=json.dumps(payload, ensure_ascii=False, indent=2),
            max_tokens=1536,
            temperature=0.3,
        )

        spec = VisualSpec(
            path=result.get("path", recommended_path),
            path_reason=result.get("path_reason", recommended_reason),
            composition=CompositionSpec.model_validate(result.get("composition", {})),
            color=ColorSpec.model_validate(result.get("color", {})),
            text_overlay=TextOverlaySpec.model_validate(result.get("text_overlay", {})),
            assets_used=[AssetUsed.model_validate(item) for item in result.get("assets_used", [])],
            path_a_prompt=result.get("path_a_prompt"),
            path_b_edit_prompt=result.get("path_b_edit_prompt"),
            path_c_template=result.get("path_c_template", "event_hero_v1"),
            path_c_use_ai_background=bool(result.get("path_c_use_ai_background", False)),
            post_type=post_type,
        )
        spec = _apply_path_rules(
            spec,
            recommended_path=recommended_path,
            post_type=post_type,
            assets_available=assets_available,
            creative_brief=creative_brief,
            profile=profile,
        )

        record = {
            **spec.model_dump(),
            "render_override": render_override,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json("visual_spec.json", record)
        mark_step_done("visual_director", next_step="image")
        return record
