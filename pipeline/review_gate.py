from __future__ import annotations

from core.job_store import read_json, update_job


def build_review_prompt(caption: dict) -> str:
    hook = caption.get("hook", "")
    hashtags = " ".join(caption.get("hashtags", [])[:5])
    return (
        "预览已生成。请审核：\n\n"
        f"Hook: {hook}\n\n"
        f"Hashtags: {hashtags}\n\n"
        "回复 ok / 发布 保存草稿\n"
        "回复 skip / 跳过 放弃本条"
    )


def apply_review(action: str) -> str:
    state = read_json("state.json")
    if state.get("status") != "waiting_review":
        return "当前没有等待审核的内容。"

    if action == "approve":
        update_job(status="approved", step="done")
        if state.get("mode") == "guided":
            return (
                "已确认草稿并保存到 state/。\n"
                "当前 MVP 还不会自动发布到 Instagram。\n"
                "下一步会接入 Ins Graph API。"
            )
        return "已确认草稿。"

    if action == "skip":
        update_job(status="skipped", step="done")
        return "已跳过当前草稿。"

    return "未知审核操作。请回复 ok / 发布 或 skip / 跳过。"
