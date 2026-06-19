from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import DATA_DIR, settings
from core.post_types import POST_TYPES

PLAYBOOK_DIR = DATA_DIR / "playbooks"
WINS_DIR = DATA_DIR / "feedback" / "wins"


def load_playbook(post_type: str) -> dict[str, Any]:
    normalized = post_type if post_type in POST_TYPES else "general"
    path = PLAYBOOK_DIR / f"{normalized}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def format_playbook_block(post_type: str) -> str:
    playbook = load_playbook(post_type)
    if not playbook:
        return ""

    composition = playbook.get("composition", {})
    lines = [
        "Playbook standards for this post_type:",
        f"- Caption: {playbook.get('caption_guidance', '')}",
        f"- Visual: {playbook.get('visual_guidance', '')}",
        f"- Path rules: {playbook.get('path_rules', '')}",
        (
            "- Composition: "
            f"{composition.get('aspect_ratio', '4:5')}, "
            f"{composition.get('resolution', '1080x1350')}, "
            f"safe zone: {composition.get('safe_zone', '')}"
        ),
    ]
    snippets = playbook.get("prompt_snippets", {})
    if snippets.get("path_b"):
        lines.append(f"- Path B prompt hint: {snippets['path_b']}")
    if snippets.get("path_a"):
        lines.append(f"- Path A prompt hint: {snippets['path_a']}")
    if snippets.get("path_c"):
        lines.append(f"- Path C prompt hint: {snippets['path_c']}")
    return "\n".join(lines)


def playbook_path_snippet(post_type: str, path: str) -> str:
    playbook = load_playbook(post_type)
    snippets = playbook.get("prompt_snippets", {})
    key = f"path_{path.lower()}"
    return str(snippets.get(key, "")).strip()


def _read_all_wins(post_type: str) -> list[dict[str, Any]]:
    path = WINS_DIR / f"{post_type}.jsonl"
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def load_win_examples(post_type: str, *, limit: int = 2) -> list[dict[str, Any]]:
    """Backward-compatible loader: returns the most recent wins."""
    rows = _read_all_wins(post_type)
    return rows[-limit:]


def load_top_win_examples(
    post_type: str,
    *,
    limit: int | None = None,
    min_score: float | None = None,
) -> list[dict[str, Any]]:
    limit = limit or settings.wins_example_limit
    min_score = settings.wins_min_score if min_score is None else min_score

    rows = _read_all_wins(post_type)
    if not rows:
        return []

    def sort_key(row: dict[str, Any]) -> tuple:
        score = row.get("overall_score")
        score_value = float(score) if isinstance(score, (int, float)) else -1.0
        saved_at = str(row.get("saved_at", ""))
        return (-score_value, saved_at)

    ranked = sorted(rows, key=sort_key)

    selected: list[dict[str, Any]] = []
    seen_hooks: set[str] = set()
    for row in ranked:
        score = row.get("overall_score")
        if min_score > 0 and isinstance(score, (int, float)) and float(score) < min_score:
            continue

        hook_key = str(row.get("hook", "")).strip().lower()[:48]
        if hook_key and hook_key in seen_hooks:
            continue
        if hook_key:
            seen_hooks.add(hook_key)

        selected.append(row)
        if len(selected) >= limit:
            break

    return selected


def format_win_examples(
    post_type: str,
    *,
    limit: int | None = None,
    min_score: float | None = None,
) -> str:
    wins = load_top_win_examples(post_type, limit=limit, min_score=min_score)
    if not wins:
        return ""

    lines = [
        "Approved win examples for this post_type (style reference only — adapt, do not copy verbatim):",
    ]
    for index, win in enumerate(wins, start=1):
        score = win.get("overall_score", "n/a")
        lines.append(f"Example {index} (human-approved, critic score {score}):")
        headline = str(win.get("headline", "")).strip()
        if headline:
            lines.append(f"  headline: {headline[:100]}")
        hook = str(win.get("hook", "")).strip()
        if hook:
            lines.append(f"  hook: {hook[:140]}")
        key_message = str(win.get("key_message", "")).strip()
        if key_message:
            lines.append(f"  key_message: {key_message[:140]}")
        scene = str(win.get("scene", "")).strip()
        if scene:
            lines.append(f"  scene: {scene[:140]}")
        path = win.get("path")
        if path:
            lines.append(f"  render_path: {path}")
        body_preview = str(win.get("body_preview", "")).strip()
        if body_preview:
            lines.append(f"  body_preview: {body_preview[:160]}")

    lines.append("Match this quality bar: clear hook, on-brief scene, appropriate render path.")
    return "\n".join(lines)


def wins_available(post_type: str) -> int:
    return len(_read_all_wins(post_type))


def ensure_playbook_dirs() -> None:
    PLAYBOOK_DIR.mkdir(parents=True, exist_ok=True)
    WINS_DIR.mkdir(parents=True, exist_ok=True)
