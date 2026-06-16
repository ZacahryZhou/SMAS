from __future__ import annotations

from pathlib import Path

from agents.caption_agent import CaptionAgent
from agents.image_agent import ImageAgent
from agents.topic_agent import TopicAgent
from core.job_store import init_job, update_job
from core.profile_store import load_profile
from pipeline.preview_composer import PreviewComposer


class ContentPipeline:
    def __init__(self) -> None:
        self.topic_agent = TopicAgent()
        self.caption_agent = CaptionAgent()
        self.image_agent = ImageAgent()
        self.preview_composer = PreviewComposer()

    def run_guided(self, user_request: str) -> Path:
        profile = load_profile()
        if not profile.is_ready_for_content():
            raise RuntimeError(
                "Brand profile is not ready. Set onboarding_complete=true and fill niche.category in "
                "data/brand_profile.json."
            )

        init_job(user_request=user_request, mode="guided")

        try:
            self.topic_agent.run(user_request, profile=profile)
            self.caption_agent.run(profile=profile)
            self.image_agent.run(profile=profile)
            preview_path = self.preview_composer.run(profile=profile)
        except Exception as exc:
            update_job(status="failed", error=str(exc))
            raise

        update_job(status="waiting_review", step="review")
        return preview_path
