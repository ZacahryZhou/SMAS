from __future__ import annotations

from core.job_store import read_json, update_job


def build_review_prompt(caption: dict) -> str:
    from core.job_store import try_read_json

    hook = caption.get("hook", "")
    hashtags = " ".join(caption.get("hashtags", [])[:5])
    post_type = caption.get("post_type", "general")
    visual_spec = try_read_json("visual_spec.json") or {}
    render_path = visual_spec.get("path", "A")
    return (
        "Preview ready. Please review:\n\n"
        f"Type: {post_type}\n"
        f"Render path: Path {render_path}\n"
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
        update_job(status="approved", step="done")
        if state.get("mode") == "guided":
            return (
                "Draft confirmed and saved to state/.\n"
                "This MVP does not publish to Instagram automatically yet.\n"
                "Instagram Graph API publishing is planned next."
            )
        return "Draft confirmed."

    if action == "skip":
        update_job(status="skipped", step="done")
        return "Current draft skipped."

    return "Unknown review action. Reply ok / publish, skip / discard, or edit: your changes."
