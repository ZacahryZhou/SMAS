from __future__ import annotations

from core.models import BrandProfile


def build_brand_context(profile: BrandProfile) -> str:
    tone = ", ".join(profile.voice.tone) or "not set"
    avoid = ", ".join(profile.voice.avoid) or "none"
    style = ", ".join(profile.visual.style_keywords) or "not set"
    palette = ", ".join(profile.visual.color_palette) or "not set"
    platforms = ", ".join(profile.account.platforms) or "instagram"

    return (
        "Brand profile context:\n"
        f"- Display name: {profile.account.display_name or 'not set'}\n"
        f"- Handle: {profile.account.handle or 'not set'}\n"
        f"- Language: {profile.account.language}\n"
        f"- Platforms: {platforms}\n"
        f"- Category: {profile.niche.category or 'not set'}\n"
        f"- Audience: {profile.niche.audience or 'not set'}\n"
        f"- Positioning: {profile.niche.positioning or 'not set'}\n"
        f"- Tone: {tone}\n"
        f"- Avoid: {avoid}\n"
        f"- CTA style: {profile.voice.cta_style or 'not set'}\n"
        f"- Visual style: {style}\n"
        f"- Color palette: {palette}\n"
        f"- No text on image: {profile.visual.no_text_on_image}\n"
        f"- Onboarding complete: {profile.onboarding_complete}"
    )


def build_profile_summary(profile: BrandProfile) -> str:
    lines = [
        "当前品牌资料库",
        f"账号名: {profile.account.display_name or '(未设置)'}",
        f"Handle: {profile.account.handle or '(未设置)'}",
        f"语言: {profile.account.language}",
        f"品类: {profile.niche.category or '(未设置)'}",
        f"受众: {profile.niche.audience or '(未设置)'}",
        f"定位: {profile.niche.positioning or '(未设置)'}",
        f"语气: {', '.join(profile.voice.tone) or '(未设置)'}",
        f"视觉风格: {', '.join(profile.visual.style_keywords) or '(未设置)'}",
        f"建档完成: {'是' if profile.onboarding_complete else '否'}",
    ]
    return "\n".join(lines)
