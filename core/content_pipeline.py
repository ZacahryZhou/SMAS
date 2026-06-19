from __future__ import annotations

from pathlib import Path

from agents.caption_agent import CaptionAgent
from agents.content_classifier import ContentClassifierAgent
from agents.creative_brief_agent import CreativeBriefAgent
from agents.critic_agent import CriticAgent
from agents.visual_director import VisualDirectorAgent
from config import settings
from core.feedback_store import save_critic_feedback
from core.job_store import init_job, mark_step_done, read_json, try_read_json, update_job, write_json
from core.pipeline_errors import TypeConfirmationRequired
from core.profile_store import load_profile
from core.type_confirm import build_type_confirmation_prompt
from pipeline.image_render import ImageRenderPipeline
from pipeline.preview_composer import PreviewComposer


#这里是在启动工具
#ContentClassifierAgent判断内容类型
#CreativeBriefAgent生成创意简报
#CaptionAgent生成文案
#VisualDirectorAgent生成图片
#ImageRenderPipeline生成图片

#这里的每一步都依赖上一步的输出作为输入然后生成新的输出
#这叫做数据依赖

#这里的是流水线 比如视觉方向是根据文案的输出来决定的原因两个1:保持一致性 2:简单可靠 3:可扩展性
class ContentPipeline:
    def __init__(self) -> None:
        self.classifier = ContentClassifierAgent()
        self.brief_agent = CreativeBriefAgent()
        self.caption_agent = CaptionAgent()
        self.visual_director = VisualDirectorAgent()
        self.image_render = ImageRenderPipeline()
        self.preview_composer = PreviewComposer()

    def _needs_type_confirmation(self, brief: dict) -> bool:
        if brief.get("user_specified_type"):
            return False
        confidence = float(brief.get("post_type_confidence", 0.0))
        return confidence < settings.type_confirm_threshold

    def _run_critic(self, profile) -> None:
        if not settings.critic_enabled:
            return
        try:
            report = CriticAgent().run(
                profile=profile,
                warn_threshold=settings.critic_warn_threshold,
            )
            state = read_json("state.json")
            save_critic_feedback(state["job_id"], report, state)
            mark_step_done("critic", next_step="review")
        except Exception:
            # Critic must never block content generation.
            return

    def _finalize_for_review(self, profile, preview_path: Path) -> Path:
        self._run_critic(profile)
        update_job(status="waiting_review", step="review")
        return preview_path

    def _run_from_brief(self, profile) -> Path:
        self.brief_agent.run(profile=profile)
        self.caption_agent.run(profile=profile)
        self.visual_director.run(profile=profile)
        self.image_render.run(profile=profile)
        preview_path = self.preview_composer.run(profile=profile)
        return preview_path

    def run_guided(self, user_request: str) -> Path:
        profile = load_profile()
        if not profile.is_ready_for_content():
            raise RuntimeError(
                "Brand profile is not ready. Set onboarding_complete=true and fill niche.category in "
                "data/brand_profile.json."
            )
        #一开始初始化开始工作前记录任务开始并且写入state.json
        init_job(user_request=user_request, mode="guided")

        try:
            self.classifier.run(user_request, profile=profile)
            brief = read_json("brief.json")
            if self._needs_type_confirmation(brief):
                update_job(status="confirm_post_type", step="classify")
                raise TypeConfirmationRequired(build_type_confirmation_prompt(brief))

            preview_path = self._run_from_brief(profile)
            preview_path = self._finalize_for_review(profile, preview_path)
        except TypeConfirmationRequired:
            raise
        except Exception as exc:
            update_job(status="failed", error=str(exc))
            raise

        return preview_path

    def continue_after_type_confirm(self, post_type: str) -> Path:
        profile = load_profile()
        state = read_json("state.json")
        if state.get("status") != "confirm_post_type":
            raise RuntimeError("No post type confirmation is pending for this job.")

        brief = read_json("brief.json")
        brief["post_type"] = post_type
        brief["post_type_confidence"] = 1.0
        brief["user_specified_type"] = post_type
        write_json("brief.json", brief)
        update_job(status="running", step="brief")

        try:
            preview_path = self._run_from_brief(profile)
            preview_path = self._finalize_for_review(profile, preview_path)
        except Exception as exc:
            update_job(status="failed", error=str(exc))
            raise

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

    @staticmethod
    def pending_type_confirmation() -> dict | None:
        state = try_read_json("state.json")
        if state and state.get("status") == "confirm_post_type":
            return state
        return None
