from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from config import STATE_DIR, ensure_dirs


def new_job_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{uuid4().hex[:6]}"


def write_json(filename: str, data: dict[str, Any]) -> Path:
    ensure_dirs()
    path = STATE_DIR / filename
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def try_read_json(filename: str) -> dict[str, Any] | None:
    path = STATE_DIR / filename
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def read_json(filename: str) -> dict[str, Any]:
    path = STATE_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing state file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def init_job(*, user_request: str, mode: str = "guided") -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    state = {
        "job_id": new_job_id(),
        "step": "classify",
        "status": "running",
        "mode": mode,
        "user_request": user_request,
        "steps_completed": [],
        "created_at": now,
        "updated_at": now,
        "error": None,
    }
    write_json("state.json", state)
    return state


def update_job(**fields: Any) -> dict[str, Any]:
    state = read_json("state.json")
    state.update(fields)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json("state.json", state)
    return state


def mark_step_done(step: str, *, next_step: str | None = None, status: str = "running") -> dict[str, Any]:
    state = read_json("state.json")
    completed = list(state.get("steps_completed", []))
    if step not in completed:
        completed.append(step)
    patch: dict[str, Any] = {
        "steps_completed": completed,
        "status": status,
    }
    if next_step is not None:
        patch["step"] = next_step
    return update_job(**patch)
