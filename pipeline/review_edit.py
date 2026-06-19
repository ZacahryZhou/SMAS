from __future__ import annotations

from pathlib import Path

from agents.visual_director import _default_assets, _overlay_from_brief
from core.edit_parser import EditRequest, parse_edit_instruction
from core.job_store import read_json, update_job, write_json
from core.profile_store import load_profile
from pipeline.image_render import ImageRenderPipeline
from pipeline.preview_composer import PreviewComposer
from pipeline.review_gate import build_review_prompt

SIZE_ORDER = ["small", "medium", "large"]


def _rerun_critic(profile) -> None:
    from config import settings
    from core.content_pipeline import ContentPipeline

    if settings.critic_enabled:
        ContentPipeline()._run_critic(profile)


def _clamp(value: float, low: float = 0.12, high: float = 0.88) -> float:
    return max(low, min(high, value))


def _bump_size(size: str, delta: int) -> str:
    index = SIZE_ORDER.index(size) if size in SIZE_ORDER else 1
    index = max(0, min(len(SIZE_ORDER) - 1, index + delta))
    return SIZE_ORDER[index]


def apply_visual_patches(spec: dict, edit: EditRequest) -> bool:
    changed = False

    if edit.path_override:
        spec["path"] = edit.path_override
        spec["path_reason"] = f"user edit: switch to Path {edit.path_override}"
        changed = True

        if edit.path_override in {"B", "C"}:
            creative_brief = read_json("creative_brief.json")
            classification = read_json("brief.json")
            assets_available = classification.get("assets_available", [])
            if not spec.get("assets_used"):
                assets = _default_assets(creative_brief, assets_available, edit.path_override)
                spec["assets_used"] = [asset.model_dump() for asset in assets]

            if edit.path_override == "C":
                overlay = _overlay_from_brief(creative_brief, spec.get("post_type", "general"))
                if not spec.get("text_overlay", {}).get("lines"):
                    spec["text_overlay"] = overlay.model_dump()

            if edit.path_override == "B" and not spec.get("assets_used"):
                spec["path"] = "A"
                spec["path_reason"] = "Path B unavailable without product asset; fell back to Path A"

    if edit.product_shift:
        composition = spec.setdefault("composition", {})
        position = list(composition.get("product_position", [0.55, 0.5]))
        if len(position) < 2:
            position = [0.55, 0.5]
        position[0] = _clamp(float(position[0]) + edit.product_shift[0])
        position[1] = _clamp(float(position[1]) + edit.product_shift[1])
        composition["product_position"] = position
        changed = True

    if edit.text_size_delta:
        overlay = spec.setdefault("text_overlay", {"enabled": True, "lines": []})
        overlay["enabled"] = True
        lines = overlay.setdefault("lines", [])
        if not lines:
            lines.append({"text": "NEW", "zone": "top-left", "size": "medium"})
        for line in lines:
            line["size"] = _bump_size(line.get("size", "medium"), edit.text_size_delta)
        changed = True

    if edit.overlay_text:
        overlay = spec.setdefault("text_overlay", {"enabled": True, "lines": []})
        overlay["enabled"] = True
        lines = overlay.setdefault("lines", [])
        if lines:
            lines[0]["text"] = edit.overlay_text.upper()
        else:
            lines.append({"text": edit.overlay_text.upper(), "zone": "top-left", "size": "large"})
        changed = True

    return changed


def summarize_edit(edit: EditRequest) -> str:
    parts: list[str] = []
    if "caption" in edit.scopes and edit.caption_note:
        parts.append(f"caption: {edit.caption_note}")
    elif "caption" in edit.scopes:
        parts.append("caption rewritten from your feedback")
    if edit.path_override:
        parts.append(f"render path {edit.path_override}")
    if edit.product_shift:
        parts.append("product position adjusted")
    if edit.text_size_delta > 0:
        parts.append("overlay text enlarged")
    elif edit.text_size_delta < 0:
        parts.append("overlay text reduced")
    if edit.overlay_text:
        parts.append(f"overlay text set to {edit.overlay_text}")
    if "image" in edit.scopes and not parts:
        parts.append("image regenerated")
    return "; ".join(parts) if parts else "changes applied"


def apply_edit_instruction(instruction: str) -> tuple[str, Path | None]:
    state = read_json("state.json")
    if state.get("status") != "waiting_review":
        raise RuntimeError("There is no content waiting for review, so it cannot be edited.")

    edit = parse_edit_instruction(instruction)
    profile = load_profile()
    pipeline = _EditPipeline()

    changes: list[str] = []

    if "caption" in edit.scopes:
        pipeline.rerun_caption(profile, edit_instruction=edit.caption_note or edit.raw_instruction)
        changes.append("caption")

    image_touched = False
    if "image" in edit.scopes:
        spec = read_json("visual_spec.json")
        patched = apply_visual_patches(spec, edit)
        if patched or edit.scopes == ["image"]:
            write_json("visual_spec.json", spec)
            pipeline.rerun_image(profile)
            image_touched = True
            changes.append("image")

    if not changes:
        raise RuntimeError("No actionable edit was recognized. Try rephrasing your request.")

    preview_path = pipeline.rerun_preview(profile)
    _rerun_critic(profile)
    update_job(status="waiting_review", step="review")

    caption = read_json("caption.json")
    summary = summarize_edit(edit)
    message = f"Updated based on your feedback ({summary}).\n\n{build_review_prompt(caption)}"
    return message, preview_path


class _EditPipeline:
    def rerun_caption(self, profile, *, edit_instruction: str) -> None:
        from agents.caption_agent import CaptionAgent

        CaptionAgent().run(profile=profile, edit_instruction=edit_instruction)

    def rerun_image(self, profile) -> None:
        ImageRenderPipeline().run(profile=profile)

    def rerun_preview(self, profile) -> Path:
        return PreviewComposer().run(profile=profile)
