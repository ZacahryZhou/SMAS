#this file 是关于总调度器，用于调度各个模块，目前有Intent Router和Orchestrator两种核心


from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from agents.profile_manager import ProfileManagerAgent
from core.brand_context import build_profile_summary
from core.content_pipeline import ContentPipeline
from core.intent_router import RoutedIntent, route_message
from core.job_store import read_json, try_read_json
from core.pipeline_errors import TypeConfirmationRequired
from core.profile_store import load_profile
from core.type_confirm import parse_type_confirmation
from pipeline.review_edit import apply_edit_instruction
from pipeline.review_gate import apply_review, build_review_prompt

from langgraph.graph import StateGraph, END


# ─────────────────────────────────────────────
# Original runtime path (Telegram bot uses this)
# ─────────────────────────────────────────────

@dataclass
class OrchestratorResult:
    text: str
    image_path: Path | None = None

#启动工具一个事负责生成内容的流水线另一个事负责管理品牌资料的agent
class Orchestrator:
    def __init__(self) -> None:
        self.pipeline = ContentPipeline()
        self.profile_agent = ProfileManagerAgent()
#handle_intent 就是一个大的分拣员。
#route_massage在贴标签是用来实现意图的
    def handle_text(self, text: str) -> OrchestratorResult:
        routed = route_message(text)
        return self.handle_intent(routed)
#设定相关的回答， 系统可以自动判断什么条件满足然后可以返回对应的节点信息
    def handle_intent(self, routed: RoutedIntent) -> OrchestratorResult:
        if routed.intent == "start":
            return OrchestratorResult(self._start_message())

        if routed.intent == "help":
            return OrchestratorResult(self._help_message())

        if routed.intent == "query_status":
            return OrchestratorResult(self._status_message())
#这里需要有做空检查是因为如果没有返回的话 系统无法在空白基础上生成内容和回复以及无法确认主题和方向所以这里需要做空检查但是下面的review不需要做空检查因为已经有一个默认的回复了
#设计原则：在数据进入核心流程之前做验证不要让垃圾数据流进系统深处
        if routed.intent == "generate_content":
            request = routed.payload.get("user_request", "").strip()
            if not request:
                return OrchestratorResult("Please tell what do you want to generate such as a post about ai agent")
            return self.generate(request)

        if routed.intent == "review_action":
            action = routed.payload.get("action", "")
            return OrchestratorResult(apply_review(action))

        if routed.intent == "review_edit":
            instruction = routed.payload.get("instruction", "").strip()
            if not instruction:
                return OrchestratorResult("Please tell how to edit, such as make it bigger / move the product to the right / change the text: make it more casual")
            return self.apply_edit(instruction)

        if routed.intent == "confirm_post_type":
            choice = routed.payload.get("choice", "").strip()
            return self.confirm_post_type(choice)

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
#这里首先保证了用户没有在审核状态然后准备调用生成的pipline进行下一步的开发，但是也提示了用户需要等待审核通过才能继续生成
#必须要检查因为run_guided会调用真实的api和fal服务会花钱 防止系统一直在调用api
    def generate(self, user_request: str) -> OrchestratorResult:
        state = try_read_json("state.json")
        if state and state.get("status") == "waiting_review":
            return OrchestratorResult(
                "The previous content is still waiting for review. Please reply ok / publish or skip / skip."
            )
        if state and state.get("status") == "confirm_post_type":
            return OrchestratorResult(
                "Please confirm the post type first. Reply 1/2/3 or type: product promo / event campaign / general."
            )

        try:
            preview_path = self.pipeline.run_guided(user_request)
        except TypeConfirmationRequired as exc:
            return OrchestratorResult(text=exc.message)
        except RuntimeError as exc:
            return OrchestratorResult(str(exc))
        except Exception as exc:
            return OrchestratorResult(f"Generation failed: {exc}")

        caption = read_json("caption.json")
        text = build_review_prompt(caption)
        return OrchestratorResult(text=text, image_path=preview_path)

    def confirm_post_type(self, choice: str) -> OrchestratorResult:
        post_type = parse_type_confirmation(choice)
        if not post_type:
            return OrchestratorResult(
                "Could not parse post type. Reply 1/2/3 or type: product promo / event campaign / general."
            )
        try:
            preview_path = self.pipeline.continue_after_type_confirm(post_type)
        except RuntimeError as exc:
            return OrchestratorResult(str(exc))
        except Exception as exc:
            return OrchestratorResult(f"Generation failed after type confirm: {exc}")

        caption = read_json("caption.json")
        text = build_review_prompt(caption)
        return OrchestratorResult(text=text, image_path=preview_path)

    def _start_message(self) -> str:
        profile = load_profile()
        ready = "Ready" if profile.is_ready_for_content() else "Not ready (please check brand_profile.json)"
        return (
            "SMAS Telegram is connected.\n"
            f"Brand profile: {ready}\n\n"
            "Common commands:\n"
            "/generate create a post about ai agent\n"
            "/profile check the profile\n"
            "/status check the current task\n"
            "/help check the help"
        )

    def _help_message(self) -> str:
        return (
            "SMAS commands:\n"
            "1. /generate <content request>   generate Ins preview\n"
            "2. if type is unclear, reply 1/2/3 or type: product promo\n"
            "3. after generating, reply ok / publish   confirm the draft\n"
            "4. reply skip / skip      discard the current draft\n"
            "5. edit the preview, such as: edit: make it bigger / move the product to the right / change the text: make it more casual\n"
            "6. /profile               check the brand profile\n"
            "7. /status                check the current task\n\n"
            "Current stage will not automatically publish to Instagram, only save the draft after review."
        )

    def _status_message(self) -> str:
        state = try_read_json("state.json")
        if not state:
            return "There is no ongoing task."

        lines = [
            f"job_id: {state.get('job_id', '-')}",
            f"step: {state.get('step', '-')}",
            f"status: {state.get('status', '-')}",
            f"request: {state.get('user_request', '-')}",
        ]
        if state.get("error"):
            lines.append(f"error: {state['error']}")
        return "\n".join(lines)


# ─────────────────────────────────────────────
# LangGraph graph (visualization only; does not affect runtime logic)
# ─────────────────────────────────────────────

class SMASState(TypedDict):
    message: str          # user original message
    intent: str           # intent after routing
    payload: dict         # parameters carried by the intent
    result_text: str      # final return text
    image_path: str | None  # preview image path (optional)


# ── Node definitions ──────────────────────────

def node_router(state: SMASState) -> SMASState:
    """parse user message, identify intent"""
    routed = route_message(state["message"])
    return {
        **state,
        "intent": routed.intent,
        "payload": routed.payload,
    }


def node_start(state: SMASState) -> SMASState:
    """Handle /start command"""
    profile = load_profile()
    ready = "Ready" if profile.is_ready_for_content() else "Not ready"
    return {
        **state,
        "result_text": f"SMAS connected. Brand profile: {ready}",
        "image_path": None,
    }


def node_help(state: SMASState) -> SMASState:
    """Return help information"""
    return {
        **state,
        "result_text": "SMAS commands: /generate /profile /status /help",
        "image_path": None,
    }


def node_status(state: SMASState) -> SMASState:
    """Query current task status"""
    job_state = try_read_json("state.json")
    if not job_state:
        text = "There is no ongoing task."
    else:
        text = f"status: {job_state.get('status', '-')}"
    return {**state, "result_text": text, "image_path": None}


def node_generate(state: SMASState) -> SMASState:
    """Generate content: classify → brief → caption → image"""
    request = state["payload"].get("user_request", "").strip()
    if not request:
        return {**state, "result_text": "Please tell me what you want to generate.", "image_path": None}

    job_state = try_read_json("state.json")
    if job_state and job_state.get("status") == "waiting_review":
        return {
            **state,
            "result_text": "The previous content is still waiting for review.",
            "image_path": None,
        }

    pipeline = ContentPipeline()
    preview_path = pipeline.run_guided(request)
    caption = read_json("caption.json")
    text = build_review_prompt(caption)
    return {
        **state,
        "result_text": text,
        "image_path": str(preview_path) if preview_path else None,
    }


def node_review_action(state: SMASState) -> SMASState:
    """Handle ok/skip review actions"""
    action = state["payload"].get("action", "")
    text = apply_review(action)
    return {**state, "result_text": text, "image_path": None}


def node_review_edit(state: SMASState) -> SMASState:
    """Handle edit instructions such as bigger text / move product right"""
    instruction = state["payload"].get("instruction", "").strip()
    if not instruction:
        return {**state, "result_text": "Please describe how you want to edit.", "image_path": None}
    try:
        text, preview_path = apply_edit_instruction(instruction)
    except RuntimeError as exc:
        return {**state, "result_text": str(exc), "image_path": None}
    return {
        **state,
        "result_text": text,
        "image_path": str(preview_path) if preview_path else None,
    }


def node_manage_profile(state: SMASState) -> SMASState:
    """Manage brand profile"""
    message = state["payload"].get("message", "").strip()
    if message.startswith("/profile"):
        text = build_profile_summary(load_profile())
    else:
        agent = ProfileManagerAgent()
        reply, _ = agent.handle_message(message)
        text = f"{reply}\n\n---\n{build_profile_summary(load_profile())}"
    return {**state, "result_text": text, "image_path": None}


def node_fallback(state: SMASState) -> SMASState:
    """Fallback for unrecognized intents"""
    return {**state, "result_text": "Unrecognized command. Type /help for assistance.", "image_path": None}


# ── Conditional routing ───────────────────────

def route_by_intent(state: SMASState) -> str:
    intent_map = {
        "start":          "start",
        "help":           "help",
        "query_status":   "status",
        "generate_content": "generate",
        "review_action":  "review_action",
        "review_edit":    "review_edit",
        "manage_profile": "manage_profile",
    }
    return intent_map.get(state["intent"], "fallback")


# ── Build graph ───────────────────────────────

def _build_graph() -> StateGraph:
    wf = StateGraph(SMASState)

    wf.add_node("router",         node_router)
    wf.add_node("start",          node_start)
    wf.add_node("help",           node_help)
    wf.add_node("status",         node_status)
    wf.add_node("generate",       node_generate)
    wf.add_node("review_action",  node_review_action)
    wf.add_node("review_edit",    node_review_edit)
    wf.add_node("manage_profile", node_manage_profile)
    wf.add_node("fallback",       node_fallback)

    wf.set_entry_point("router")

    wf.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "start":          "start",
            "help":           "help",
            "status":         "status",
            "generate":       "generate",
            "review_action":  "review_action",
            "review_edit":    "review_edit",
            "manage_profile": "manage_profile",
            "fallback":       "fallback",
        },
    )

    for node in ["start", "help", "status", "generate",
                 "review_action", "review_edit", "manage_profile", "fallback"]:
        wf.add_edge(node, END)

    return wf


# langgraph dev expects this variable name
graph = _build_graph().compile()
