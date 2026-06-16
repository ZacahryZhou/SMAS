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
