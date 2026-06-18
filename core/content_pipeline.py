from __future__ import annotations

from pathlib import Path

from agents.caption_agent import CaptionAgent
from agents.content_classifier import ContentClassifierAgent
from agents.creative_brief_agent import CreativeBriefAgent
from agents.visual_director import VisualDirectorAgent
from core.job_store import init_job, read_json, update_job
from core.profile_store import load_profile
from pipeline.image_render import ImageRenderPipeline
from pipeline.preview_composer import PreviewComposer


class ContentPipeline:
    def __init__(self) -> None:
        self.classifier = ContentClassifierAgent()
        self.brief_agent = CreativeBriefAgent()
        self.caption_agent = CaptionAgent()
        self.visual_director = VisualDirectorAgent()
        self.image_render = ImageRenderPipeline()
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
            self.classifier.run(user_request, profile=profile)
            self.brief_agent.run(profile=profile)
            self.caption_agent.run(profile=profile)
            self.visual_director.run(profile=profile)
            self.image_render.run(profile=profile)
            preview_path = self.preview_composer.run(profile=profile)
        except Exception as exc:
            update_job(status="failed", error=str(exc))
            raise

        update_job(status="waiting_review", step="review")
        return preview_path

    def apply_edit(self, instruction: str) -> Path:
        from pipeline.review_edit import apply_edit_instruction

        _, preview_path = apply_edit_instruction(instruction)
        if preview_path is None:
            raise RuntimeError("Edit failed: no new preview image was generated.")
        return preview_path

    def last_post_type(self) -> str:
        brief = read_json("brief.json")
        return brief.get("post_type", "general")

    def last_render_path(self) -> str:
        spec = read_json("visual_spec.json")
        return spec.get("path", "A")
