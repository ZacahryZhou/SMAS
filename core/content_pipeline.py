from __future__ import annotations

from pathlib import Path

from agents.caption_agent import CaptionAgent
from agents.content_classifier import ContentClassifierAgent
from agents.creative_brief_agent import CreativeBriefAgent
from agents.critic_agent import CriticAgent
from agents.visual_director import VisualDirectorAgent
from config import settings
from core.asset_alignment import apply_asset_alignment
from core.auto_refine import build_refine_record, choose_refine_scope, should_auto_refine
from core.feedback_store import save_critic_feedback
from core.job_store import init_job, mark_step_done, read_json, try_read_json, update_job, write_json
from core.pipeline_errors import TypeConfirmationRequired
from core.profile_store import load_profile
from core.type_confirm import build_type_confirmation_prompt
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

    def _needs_type_confirmation(self, brief: dict) -> bool:
        if brief.get("user_specified_type"):
            return False
        confidence = float(brief.get("post_type_confidence", 0.0))
        return confidence < settings.type_confirm_threshold

    def _apply_asset_alignment_step(self, profile) -> dict:
        if not settings.asset_alignment_enabled:
            return {"checked": False, "skipped": True}
        creative_brief = read_json("creative_brief.json")
        classification = read_json("brief.json")
        visual_spec = read_json("visual_spec.json")
        report = apply_asset_alignment(
            visual_spec,
            creative_brief=creative_brief,
            classification=classification,
        )
        write_json("visual_spec.json", visual_spec)
        mark_step_done("asset_alignment", next_step="image")
        return report

    def _run_render_and_preview(self, profile) -> Path:
        self.image_render.run(profile=profile)
        return self.preview_composer.run(profile=profile)

    def _run_critic(self, profile) -> dict | None:
        if not settings.critic_enabled:
            return None
        try:
            report = CriticAgent().run(
                profile=profile,
                warn_threshold=settings.critic_warn_threshold,
            )
            state = read_json("state.json")
            save_critic_feedback(state["job_id"], report, state)
            mark_step_done("critic", next_step="review")
            return report
        except Exception:
            return None

    def _run_refine_pass(self, profile, *, scope: str) -> None:
        if scope == "caption":
            self.caption_agent.run(profile=profile)
            self.preview_composer.run(profile=profile)
            mark_step_done("auto_refine_caption", next_step="review")
            return

        self.visual_director.run(profile=profile)
        self._apply_asset_alignment_step(profile)
        self._run_render_and_preview(profile)
        mark_step_done("auto_refine_visual", next_step="review")

    def _maybe_auto_refine(self, profile, *, initial_report: dict | None) -> dict | None:
        if not initial_report:
            return None

        state = read_json("state.json")
        retry_count = int((state.get("auto_refine") or {}).get("attempts", 0))
        alignment_report = try_read_json("asset_alignment.json")

        do_refine, reason = should_auto_refine(
            initial_report,
            alignment_report=alignment_report,
            retry_count=retry_count,
            max_retries=settings.auto_refine_max_retries,
            score_threshold=settings.auto_refine_score_threshold,
            enabled=settings.auto_refine_enabled,
        )
        if not do_refine:
            return initial_report

        scope = choose_refine_scope(initial_report, alignment_report=alignment_report)
        update_job(step="auto_refine", status="running")
        self._run_refine_pass(profile, scope=scope)

        after_report = self._run_critic(profile) or initial_report
        refine_record = build_refine_record(
            scope=scope,
            reason=reason,
            attempt=retry_count + 1,
            before_report=initial_report,
            after_report=after_report,
        )
        history = list((state.get("auto_refine") or {}).get("history", []))
        history.append(refine_record)
        update_job(
            auto_refine={
                "attempts": retry_count + 1,
                "last_scope": scope,
                "last_reason": reason,
                "history": history,
            }
        )
        return after_report

    def _finalize_for_review(self, profile, preview_path: Path) -> Path:
        initial_report = self._run_critic(profile)
        self._maybe_auto_refine(profile, initial_report=initial_report)
        update_job(status="waiting_review", step="review")
        return preview_path

    def _run_from_brief(self, profile) -> Path:
        self.brief_agent.run(profile=profile)
        self.caption_agent.run(profile=profile)
        self.visual_director.run(profile=profile)
        self._apply_asset_alignment_step(profile)
        preview_path = self._run_render_and_preview(profile)
        return preview_path

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
