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
            self.brief_agent.run(profile=profile)
            self.caption_agent.run(profile=profile)
            self.visual_director.run(profile=profile)
            self.image_render.run(profile=profile)
            preview_path = self.preview_composer.run(profile=profile)
        except Exception as exc:
            update_job(status="failed", error=str(exc))
            raise
#完成工作后更新任务状态为waiting_review并且写入state.json
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

'''
整个流程是从用户输入信息
-> intent router identifies the intent(labeling the message)
-> orchestrator dispatches to the right handler
-> ContentPipline generate the whole content(executes)
→ init_job records the start
→ 6 agents run in sequence
   Classifier → Brief → Caption → Visual → Image → Composer
→ update_job records completion (status: waiting_review)
→ orchestrator returns preview to user for review
'''