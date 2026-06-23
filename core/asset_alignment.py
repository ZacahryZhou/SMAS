from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.job_store import write_json

# Category tags inferred from brief text or asset filenames.
_CATEGORY_KEYWORDS: dict[str, set[str]] = {
    "gelato": {"gelato", "gelato", "ice cream", "scoop", "dessert", "frozen", "冰淇淋", "雪糕"},
    "bottle": {"bottle", "drink", "beverage", "water bottle", "水瓶", "瓶子", "sample_bottle"},
    "coffee": {"coffee", "espresso", "latte", "cappuccino", "cafe", "咖啡", "浓缩"},
    "bowl": {"bowl", "ceramic", "dish", "碗", "盛"},
}

# If brief implies left category, asset strongly tagged as right category → mismatch.
_CONFLICTS: list[tuple[set[str], set[str]]] = [
    ({"gelato", "bowl"}, {"bottle"}),
    ({"gelato"}, {"bottle"}),
    ({"coffee"}, {"bottle"}),
    ({"bowl"}, {"bottle"}),
]


def build_product_corpus(*, creative_brief: dict, classification: dict | None = None) -> str:
    parts: list[str] = []
    if classification:
        parts.append(str(classification.get("user_request", "")))
        parts.append(str(classification.get("user_intent", "")))
    parts.extend(
        [
            str(creative_brief.get("headline", "")),
            str(creative_brief.get("key_message", "")),
            str((creative_brief.get("visual") or {}).get("scene", "")),
            str((creative_brief.get("visual") or {}).get("product_placement", "")),
        ]
    )
    return " ".join(part for part in parts if part.strip()).lower()


def _detect_categories(text: str) -> set[str]:
    lowered = text.lower()
    found: set[str] = set()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            found.add(category)
    return found


def score_asset_fit(asset_path: str, corpus: str) -> float:
    """Return 0.0 (clear mismatch) .. 1.0 (clear match). 0.5 = unknown/neutral."""
    corpus_categories = _detect_categories(corpus)
    asset_text = f"{Path(asset_path).stem} {asset_path}".lower()
    asset_categories = _detect_categories(asset_text)

    if not asset_categories:
        return 0.5
    if not corpus_categories:
        return 0.5
    if corpus_categories & asset_categories:
        return 1.0

    for expected, forbidden in _CONFLICTS:
        if corpus_categories & expected and asset_categories & forbidden:
            return 0.0

    return 0.35


def pick_best_asset(assets_available: list[str], corpus: str) -> str | None:
    if not assets_available:
        return None

    scored = [(score_asset_fit(path, corpus), path) for path in assets_available]
    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_path = scored[0]
    if best_score >= 0.5:
        return best_path
    return None


def _issue_from_scores(asset_path: str, fit_score: float, corpus: str) -> str | None:
    if fit_score > 0.45:
        return None
    return (
        f"Asset '{asset_path}' may not match the brief product scene "
        f"(fit={fit_score:.2f}; brief mentions: {', '.join(sorted(_detect_categories(corpus))) or 'general scene'})"
    )


def apply_asset_alignment(
    visual_spec: dict[str, Any],
    *,
    creative_brief: dict,
    classification: dict,
) -> dict[str, Any]:
    """
    Rank 2: pre-render asset alignment.
    Patches visual_spec in place and returns an alignment report.
    """
    report: dict[str, Any] = {
        "checked": True,
        "issues": [],
        "actions": [],
        "asset_scores": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    path = str(visual_spec.get("path", "A")).upper()
    if path not in {"B", "C"}:
        write_json("asset_alignment.json", report)
        return report

    corpus = build_product_corpus(creative_brief=creative_brief, classification=classification)
    assets_available = list(classification.get("assets_available") or [])
    assets_used = list(visual_spec.get("assets_used") or [])

    if not assets_used and assets_available:
        report["issues"].append("Path B/C selected but visual_spec.assets_used is empty.")
        best = pick_best_asset(assets_available, corpus)
        if best:
            visual_spec["assets_used"] = [
                {"path": best, "role": "hero_product", "needs_cutout": path == "C"}
            ]
            report["actions"].append(f"Inserted best-fit asset '{best}'.")
        elif path == "B":
            visual_spec["path"] = "A"
            visual_spec["path_reason"] = (
                "Asset alignment: no suitable product asset for Path B; fallback to Path A."
            )
            visual_spec["assets_used"] = []
            report["actions"].append("Fallback Path B → A (no aligned asset).")
        write_json("asset_alignment.json", report)
        return report

    for entry in assets_used:
        asset_path = str(entry.get("path", "")).strip()
        if not asset_path:
            continue
        fit = score_asset_fit(asset_path, corpus)
        report["asset_scores"][asset_path] = round(fit, 3)
        issue = _issue_from_scores(asset_path, fit, corpus)
        if issue:
            report["issues"].append(issue)

    if not report["issues"]:
        write_json("asset_alignment.json", report)
        return report

    current_path = str(assets_used[0].get("path", "")) if assets_used else ""
    current_score = report["asset_scores"].get(current_path, 0.5)
    best = pick_best_asset(assets_available, corpus)
    best_score = score_asset_fit(best, corpus) if best else 0.0

    if best and best != current_path and best_score > current_score + 0.15:
        visual_spec["assets_used"] = [
            {
                **assets_used[0],
                "path": best,
                "role": assets_used[0].get("role", "hero_product"),
            }
        ]
        report["actions"].append(
            f"Replaced '{current_path}' with better-fit asset '{best}' "
            f"(score {current_score:.2f} → {best_score:.2f})."
        )
        visual_spec["path_reason"] = (
            str(visual_spec.get("path_reason", "")).strip()
            + " Asset alignment replaced mismatched product reference."
        ).strip()
    elif path == "B" and current_score < 0.45:
        visual_spec["path"] = "A"
        visual_spec["assets_used"] = []
        visual_spec["path_reason"] = (
            f"Asset alignment: '{current_path}' mismatches brief; fallback to Path A scene generation."
        )
        report["actions"].append(f"Fallback Path B → A due to asset mismatch on '{current_path}'.")

    write_json("asset_alignment.json", report)
    return report


def alignment_needs_refine(report: dict[str, Any] | None) -> bool:
    if not report:
        return False
    return bool(report.get("issues")) and not report.get("actions")
