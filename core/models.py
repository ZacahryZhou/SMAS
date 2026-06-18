from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AccountProfile(BaseModel):
    display_name: str = ""
    handle: str = ""
    language: str = "en"
    platforms: list[str] = Field(default_factory=lambda: ["instagram"])


class NicheProfile(BaseModel):
    category: str = ""
    audience: str = ""
    positioning: str = ""


class VoiceProfile(BaseModel):
    tone: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    cta_style: str = ""


class VisualProfile(BaseModel):
    style_keywords: list[str] = Field(default_factory=list)
    color_palette: list[str] = Field(default_factory=list)
    no_text_on_image: bool = True


class TopicSource(BaseModel):
    type: str
    enabled: bool = True
    url: str | None = None
    subreddit: str | None = None
    weight: float = 1.0


class BrandProfile(BaseModel):
    account: AccountProfile = Field(default_factory=AccountProfile)
    niche: NicheProfile = Field(default_factory=NicheProfile)
    voice: VoiceProfile = Field(default_factory=VoiceProfile)
    visual: VisualProfile = Field(default_factory=VisualProfile)
    topic_sources: list[TopicSource] = Field(default_factory=list)
    onboarding_complete: bool = False
    updated_at: str | None = None

    def is_ready_for_content(self) -> bool:
        return self.onboarding_complete and bool(self.niche.category.strip())


class ProfileAgentResponse(BaseModel):
    reply_to_user: str
    patch: dict[str, Any] = Field(default_factory=dict)
    onboarding_complete: bool | None = None


class TextOnImageSpec(BaseModel):
    enabled: bool = False
    elements: list[str] = Field(default_factory=list)
    style: str = ""


class VisualBrief(BaseModel):
    scene: str = ""
    product_placement: str = ""
    composition: str = ""
    color_mood: str = ""
    text_on_image: TextOnImageSpec = Field(default_factory=TextOnImageSpec)
    use_user_assets: bool = False
    asset_roles: dict[str, str] = Field(default_factory=dict)


class BriefClassification(BaseModel):
    post_type: str
    post_type_confidence: float = 0.0
    user_intent: str = ""
    goal: str = ""
    audience_focus: str = ""
    reason: str = ""
    user_request: str = ""
    assets_available: list[str] = Field(default_factory=list)
    user_specified_type: str | None = None


class CreativeBrief(BaseModel):
    post_type: str
    user_request: str = ""
    headline: str = ""
    key_message: str = ""
    caption_angle: str = ""
    cta_hint: str = ""
    title: str = ""
    angle: str = ""
    visual: VisualBrief = Field(default_factory=VisualBrief)


class TextOverlayLine(BaseModel):
    text: str
    zone: str = "top-left"
    size: str = "medium"


class TextOverlaySpec(BaseModel):
    enabled: bool = False
    lines: list[TextOverlayLine] = Field(default_factory=list)


class CompositionSpec(BaseModel):
    layout: str = "hero_center"
    product_position: list[float] = Field(default_factory=lambda: [0.55, 0.5])
    text_safe_zones: list[str] = Field(default_factory=list)


class ColorSpec(BaseModel):
    background: str = "#F5F0EB"
    accent: str = "#E85D4C"
    mood: str = ""


class AssetUsed(BaseModel):
    path: str
    role: str = "hero_product"
    needs_cutout: bool = True


class VisualSpec(BaseModel):
    path: str
    path_reason: str = ""
    composition: CompositionSpec = Field(default_factory=CompositionSpec)
    color: ColorSpec = Field(default_factory=ColorSpec)
    text_overlay: TextOverlaySpec = Field(default_factory=TextOverlaySpec)
    assets_used: list[AssetUsed] = Field(default_factory=list)
    path_a_prompt: str | None = None
    path_b_edit_prompt: str | None = None
    path_c_template: str = "event_hero_v1"
    path_c_use_ai_background: bool = False
    post_type: str = "general"
