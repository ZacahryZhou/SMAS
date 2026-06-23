from __future__ import annotations

import re
from typing import Any, Literal

RefineScope = Literal["caption", "visual"]

_ASSET_ISSUE_RE = re.compile(
    r"asset|mismatch|sample_bottle|bottle|gelato|product photo|reference product|hero product",
    re.IGNORECASE,
)


def _numeric(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def critic_flags_asset_issue(critic_report: dict[str, Any]) -> bool:
    chunks: list[str] = []
    chunks.extend(str(item) for item in critic_report.get("issues", []))
    chunks.extend(str(item) for item in critic_report.get("suggestions", []))
    text = " ".join(chunks)
    return bool(_ASSET_ISSUE_RE.search(text))


def choose_refine_scope(
    critic_report: dict[str, Any],
    *,
    alignment_report: dict[str, Any] | None = None,
) -> RefineScope:
    alignment_issues = bool(alignment_report and alignment_report.get("issues"))
    asset_critic = critic_flags_asset_issue(critic_report)

    caption = _numeric(critic_report.get("caption_score"))
    visual = _numeric(critic_report.get("visual_score"))
    alignment = _numeric(critic_report.get("alignment_score"))

    if alignment_issues or asset_critic:
        return "visual"

    scores = {"caption": caption, "visual": visual, "alignment": alignment}
    available = {key: value for key, value in scores.items() if value is not None}
    if not available:
        return "caption"

    lowest_key = min(available, key=lambda key: available[key])
    if lowest_key == "caption":
        return "caption"
    return "visual"


def should_auto_refine(
    critic_report: dict[str, Any],
    *,
    alignment_report: dict[str, Any] | None = None,
    retry_count: int = 0,
    max_retries: int = 1,
    score_threshold: float = 6.0,
    enabled: bool = True,
) -> tuple[bool, str]:
    if not enabled:
        return False, "auto_refine disabled"
    if retry_count >= max_retries:
        return False, "max auto-refine retries reached"

    overall = _numeric(critic_report.get("overall_score"))
    if critic_report.get("error"):
        return False, "critic unavailable"

    alignment_issues = bool(alignment_report and alignment_report.get("issues"))
    asset_critic = critic_flags_asset_issue(critic_report)
    low_score = overall is not None and overall < score_threshold
    warn = bool(critic_report.get("low_quality_warning"))

    if alignment_issues and not alignment_report.get("actions"):
        return True, "asset alignment unresolved"
    if asset_critic:
        return True, "critic flagged asset/visual mismatch"
    if low_score or warn:
        return True, f"overall score below threshold ({overall})"

    return False, "quality acceptable"


def build_refine_record(
    *,
    scope: RefineScope,
    reason: str,
    attempt: int,
    before_report: dict[str, Any],
    after_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "attempt": attempt,
        "scope": scope,
        "reason": reason,
        "before_overall": before_report.get("overall_score"),
        "after_overall": (after_report or {}).get("overall_score"),
    }
    if after_report:
        record["improved"] = (
            _numeric(after_report.get("overall_score")) or 0
        ) > (_numeric(before_report.get("overall_score")) or 0)
    return record
