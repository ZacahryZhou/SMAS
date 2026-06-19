from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import DATA_DIR

FEEDBACK_DIR = DATA_DIR / "feedback"
JOBS_DIR = FEEDBACK_DIR / "jobs"
WINS_DIR = FEEDBACK_DIR / "wins"


def ensure_feedback_dirs() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    WINS_DIR.mkdir(parents=True, exist_ok=True)


def save_job_feedback(job_id: str, record: dict[str, Any]) -> Path:
    ensure_feedback_dirs()
    path = JOBS_DIR / f"{job_id}.json"
    payload = {
        **record,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def append_win_example(post_type: str, record: dict[str, Any]) -> Path:
    ensure_feedback_dirs()
    path = WINS_DIR / f"{post_type}.jsonl"
    payload = {
        **record,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path


def build_job_record(
    state: dict[str, Any],
    *,
    action: str | None = None,
    critic_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from core.job_store import try_read_json

    brief = try_read_json("brief.json") or {}
    caption = try_read_json("caption.json") or {}
    creative = try_read_json("creative_brief.json") or {}
    visual = try_read_json("visual_spec.json") or {}
    critic = critic_report or try_read_json("critic_report.json") or {}
    post_type = brief.get("post_type", caption.get("post_type", "general"))

    record: dict[str, Any] = {
        "job_id": state.get("job_id", "unknown"),
        "post_type": post_type,
        "user_request": state.get("user_request", ""),
        "path": visual.get("path"),
        "path_reason": visual.get("path_reason"),
        "hook": caption.get("hook"),
        "scene": (creative.get("visual") or {}).get("scene"),
        "critic": {
            "overall_score": critic.get("overall_score"),
            "caption_score": critic.get("caption_score"),
            "visual_score": critic.get("visual_score"),
            "alignment_score": critic.get("alignment_score"),
            "summary": critic.get("summary"),
            "issues": critic.get("issues", []),
            "suggestions": critic.get("suggestions", []),
        },
    }
    if action:
        record["action"] = action
    return record


def build_win_record(state: dict[str, Any]) -> dict[str, Any]:
    from core.job_store import try_read_json

    record = build_job_record(state, action="approve")
    caption = try_read_json("caption.json") or {}
    creative = try_read_json("creative_brief.json") or {}
    brief_refs = caption.get("brief_refs") or {}

    return {
        "post_type": record.get("post_type"),
        "hook": record.get("hook", ""),
        "headline": brief_refs.get("headline") or creative.get("headline", ""),
        "key_message": brief_refs.get("key_message") or creative.get("key_message", ""),
        "scene": record.get("scene", ""),
        "path": record.get("path", ""),
        "body_preview": str(caption.get("body", "")).strip()[:200],
        "overall_score": (record.get("critic") or {}).get("overall_score"),
    }


def save_critic_feedback(job_id: str, critic_report: dict[str, Any], state: dict[str, Any]) -> Path:
    record = build_job_record(state, action="generated", critic_report=critic_report)
    return save_job_feedback(job_id, record)
