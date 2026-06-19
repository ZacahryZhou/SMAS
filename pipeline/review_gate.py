from __future__ import annotations

from agents.critic_agent import format_critic_summary
from core.feedback_store import append_win_example, build_job_record, build_win_record, save_job_feedback
from core.job_store import read_json, try_read_json, update_job


def build_review_prompt(caption: dict) -> str:
    hook = caption.get("hook", "")
    hashtags = " ".join(caption.get("hashtags", [])[:5])
    post_type = caption.get("post_type", "general")
    visual_spec = try_read_json("visual_spec.json") or {}
    critic_report = try_read_json("critic_report.json") or {}
    render_path = visual_spec.get("path", "A")
    brief_refs = caption.get("brief_refs") or {}
    visual_refs = visual_spec.get("brief_refs") or {}
    headline = brief_refs.get("headline", "")
    scene = visual_refs.get("scene") or brief_refs.get("visual_scene", "")
    alignment_lines = []
    if headline:
        alignment_lines.append(f"Headline: {headline}")
    if scene:
        alignment_lines.append(f"Scene: {scene}")
    alignment_block = "\n".join(alignment_lines)
    if alignment_block:
        alignment_block += "\n\n"

    critic_block = format_critic_summary(critic_report)
    if critic_block:
        critic_block += "\n\n"

    return (
        "Preview ready. Please review:\n\n"
        f"Type: {post_type}\n"
        f"Render path: Path {render_path}\n"
        f"{alignment_block}"
        f"{critic_block}"
        f"Hook: {hook}\n\n"
        f"Hashtags: {hashtags}\n\n"
        "Reply ok / publish to save the draft\n"
        "Reply skip / discard to drop this draft\n"
        "Reply edit: ... or try bigger text / move product right / path: C / caption: ..."
    )


def apply_review(action: str) -> str:
    state = read_json("state.json")
    if state.get("status") != "waiting_review":
        return "There is no content waiting for review."

    if action == "approve":
        record = build_job_record(state, action="approve")
        save_job_feedback(record["job_id"], record)
        append_win_example(record["post_type"], build_win_record(state))
        update_job(status="approved", step="done")
        if state.get("mode") == "guided":
            return (
                "Draft confirmed and saved to state/.\n"
                "Feedback and critic scores saved for future prompt examples.\n"
                "This MVP does not publish to Instagram automatically yet.\n"
                "Instagram Graph API publishing is planned next."
            )
        return "Draft confirmed."

    if action == "skip":
        record = build_job_record(state, action="skip")
        save_job_feedback(record["job_id"], record)
        update_job(status="skipped", step="done")
        return "Current draft skipped. Feedback saved."

    return "Unknown review action. Reply ok / publish, skip / discard, or edit: your changes."
