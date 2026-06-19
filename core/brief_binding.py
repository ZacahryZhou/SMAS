from __future__ import annotations

CAPTION_REQUIRED_FIELDS = ("headline", "key_message", "caption_angle", "cta_hint")
VISUAL_REQUIRED_FIELDS = ("scene", "product_placement", "composition", "color_mood")


def extract_caption_directives(brief: dict) -> dict:
    visual = brief.get("visual") or {}
    return {
        "headline": brief.get("headline", ""),
        "key_message": brief.get("key_message", ""),
        "caption_angle": brief.get("caption_angle", ""),
        "cta_hint": brief.get("cta_hint", ""),
        "visual_scene": visual.get("scene", ""),
    }


def extract_visual_directives(brief: dict) -> dict:
    visual = brief.get("visual") or {}
    return {
        "scene": visual.get("scene", ""),
        "product_placement": visual.get("product_placement", ""),
        "composition": visual.get("composition", ""),
        "color_mood": visual.get("color_mood", ""),
        "text_on_image": visual.get("text_on_image", {}),
        "use_user_assets": visual.get("use_user_assets", False),
        "asset_roles": visual.get("asset_roles", {}),
    }


def extract_caption_context(caption: dict) -> dict:
    """Secondary context for Visual Director — tone only, not scene authority."""
    return {
        "hook": caption.get("hook", ""),
        "alt_text": caption.get("alt_text", ""),
    }


def caption_binding_rules() -> str:
    return """
Brief binding rules (mandatory):
- hook must reflect headline and key_message; do not invent a different topic
- body must expand key_message using caption_angle
- for product_promo, all 3 body bullets must support key_message
- cta must follow cta_hint closely
- alt_text must describe visual_scene from the brief
- Do not contradict creative_brief fields
""".strip()


def visual_binding_rules() -> str:
    return """
Brief binding rules (mandatory):
- creative_brief.visual is the PRIMARY source for scene, placement, composition, color_mood
- caption is SECONDARY: use hook/alt_text only for tone consistency, never to override visual.scene
- path_a_prompt and path_b_edit_prompt must describe creative_brief.visual.scene
- text_overlay elements must come from creative_brief.visual.text_on_image when enabled
- Do not invent a scene that conflicts with creative_brief.visual.scene
""".strip()


def missing_brief_fields(brief: dict) -> list[str]:
    missing: list[str] = []
    for field in CAPTION_REQUIRED_FIELDS:
        if not str(brief.get(field, "")).strip():
            missing.append(field)

    visual = brief.get("visual") or {}
    for field in VISUAL_REQUIRED_FIELDS:
        if not str(visual.get(field, "")).strip():
            missing.append(f"visual.{field}")
    return missing
