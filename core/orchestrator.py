from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agents.profile_manager import ProfileManagerAgent
from core.brand_context import build_profile_summary
from core.content_pipeline import ContentPipeline
from core.intent_router import RoutedIntent, route_message
from core.job_store import read_json, try_read_json
from core.profile_store import load_profile
from pipeline.review_edit import apply_edit_instruction
from pipeline.review_gate import apply_review, build_review_prompt


@dataclass
class OrchestratorResult:
    text: str
    image_path: Path | None = None


class Orchestrator:
    def __init__(self) -> None:
        self.pipeline = ContentPipeline()
        self.profile_agent = ProfileManagerAgent()

    def handle_text(self, text: str) -> OrchestratorResult:
        routed = route_message(text)
        return self.handle_intent(routed)

    def handle_intent(self, routed: RoutedIntent) -> OrchestratorResult:
        if routed.intent == "start":
            return OrchestratorResult(self._start_message())

        if routed.intent == "help":
            return OrchestratorResult(self._help_message())

        if routed.intent == "query_status":
            return OrchestratorResult(self._status_message())

        if routed.intent == "generate_content":
            request = routed.payload.get("user_request", "").strip()
            if not request:
                return OrchestratorResult("请告诉我你想生成什么内容。例如：做一条关于 AI agent 的帖")
            return self.generate(request)

        if routed.intent == "review_action":
            action = routed.payload.get("action", "")
            return OrchestratorResult(apply_review(action))

        if routed.intent == "review_edit":
            instruction = routed.payload.get("instruction", "").strip()
            if not instruction:
                return OrchestratorResult("请说明要如何修改，例如：字大一点 / 商品往右 / 改文案：语气更轻松")
            return self.apply_edit(instruction)

        if routed.intent == "manage_profile":
            message = routed.payload.get("message", "").strip()
            if message.startswith("/profile"):
                return OrchestratorResult(build_profile_summary(load_profile()))
            reply, _ = self.profile_agent.handle_message(message)
            return OrchestratorResult(f"{reply}\n\n---\n{build_profile_summary(load_profile())}")

        return OrchestratorResult(self._help_message())

    def apply_edit(self, instruction: str) -> OrchestratorResult:
        try:
            text, preview_path = apply_edit_instruction(instruction)
        except RuntimeError as exc:
            return OrchestratorResult(str(exc))
        return OrchestratorResult(text=text, image_path=preview_path)

    def generate(self, user_request: str) -> OrchestratorResult:
        state = try_read_json("state.json")
        if state and state.get("status") == "waiting_review":
            return OrchestratorResult(
                "上一条内容还在等待审核。请先回复 ok / 发布 或 skip / 跳过。"
            )

        preview_path = self.pipeline.run_guided(user_request)
        caption = read_json("caption.json")
        text = build_review_prompt(caption)
        return OrchestratorResult(text=text, image_path=preview_path)

    def _start_message(self) -> str:
        profile = load_profile()
        ready = "已就绪" if profile.is_ready_for_content() else "未就绪（请检查 brand_profile.json）"
        return (
            "SMAS Telegram 已连接。\n"
            f"品牌资料库：{ready}\n\n"
            "常用指令：\n"
            "/generate 做一条关于 AI agent 的帖\n"
            "/profile 查看资料库\n"
            "/status 查看当前任务\n"
            "/help 查看帮助"
        )

    def _help_message(self) -> str:
        return (
            "SMAS 指令：\n"
            "1. /generate <内容需求>  生成 Ins 预览\n"
            "2. 生成后回复 ok / 发布  确认草稿\n"
            "3. 回复 skip / 跳过      放弃当前草稿\n"
            "4. 修改预览，例如：\n"
            "   edit: 字大一点\n"
            "   商品往右 / 路径：C\n"
            "   改文案：语气更轻松\n"
            "5. /profile              查看品牌资料\n"
            "6. /status               查看任务状态\n\n"
            "当前阶段不会自动发布到 Instagram，审核通过只会保存草稿。"
        )

    def _status_message(self) -> str:
        state = try_read_json("state.json")
        if not state:
            return "当前没有进行中的任务。"

        lines = [
            f"job_id: {state.get('job_id', '-')}",
            f"step: {state.get('step', '-')}",
            f"status: {state.get('status', '-')}",
            f"request: {state.get('user_request', '-')}",
        ]
        if state.get("error"):
            lines.append(f"error: {state['error']}")
        return "\n".join(lines)
