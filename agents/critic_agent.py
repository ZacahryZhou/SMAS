from __future__ import annotations

import json
from datetime import datetime, timezone
from statistics import mean

from core.brand_context import build_brand_context
from core.brief_binding import extract_caption_directives, extract_visual_directives
from core.job_store import read_json, try_read_json, write_json
from core.models import BrandProfile
from core.profile_store import load_profile
from core.playbook import format_win_examples
from tools.deepseek_client import DeepSeekClient

SYSTEM_PROMPT = """
You are the Critic Agent for SMAS, evaluating an Instagram draft before human review.

Score each dimension from 1 to 10 (integers):
- caption_score: hook/body/cta quality, brand fit, structure for post_type
- visual_score: scene clarity, Instagram suitability, path choice fit
- alignment_score: caption and visual both reflect the same creative_brief (headline, key_message, scene)

Also provide:
- overall_score: integer 1-10, your holistic judgment (not a strict average)
- issues: up to 3 short bullet strings describing problems
- suggestions: up to 3 short actionable fixes the user or edit step could apply
- summary: one sentence overall assessment

Be practical and strict. Penalize:
- caption hook ignoring headline or key_message
- visual scene diverging from creative_brief.visual.scene
- weak CTA, generic hashtags, or wrong post_type structure
- product_promo without clear product benefit

When approved_benchmarks are provided, compare the draft against those human-approved examples.
Score lower if the draft is clearly weaker than the benchmarks on clarity, alignment, or brand fit.

Output valid json only:
{
  "caption_score": 8,
  "visual_score": 7,
  "alignment_score": 8,
  "overall_score": 7,
  "issues": ["..."],
  "suggestions": ["..."],
  "summary": "..."
}
""".strip()


def format_critic_summary(report: dict) -> str:
    if not report:
        return ""

    if report.get("error"):
        return f"Critic: unavailable ({report['error']})"

    overall = report.get("overall_score", "-")
    caption = report.get("caption_score", "-")
    visual = report.get("visual_score", "-")
    alignment = report.get("alignment_score", "-")
    lines = [
        f"Critic scores: overall {overall}/10 | caption {caption} | visual {visual} | alignment {alignment}",
    ]
    summary = str(report.get("summary", "")).strip()
    if summary:
        lines.append(f"Summary: {summary}")

    issues = [str(item).strip() for item in report.get("issues", []) if str(item).strip()]
    if issues:
        lines.append("Issues:")
        lines.extend(f"- {issue}" for issue in issues[:3])

    suggestions = [str(item).strip() for item in report.get("suggestions", []) if str(item).strip()]
    if suggestions:
        lines.append("Suggestions:")
        lines.extend(f"- {item}" for item in suggestions[:3])

    if report.get("low_quality_warning"):
        lines.append("Note: score is below quality threshold — consider edit before publishing.")

    return "\n".join(lines)


def _fallback_report(error: str) -> dict:
    return {
        "caption_score": None,
        "visual_score": None,
        "alignment_score": None,
        "overall_score": None,
        "issues": [],
        "suggestions": [],
        "summary": "Critic could not run for this draft.",
        "error": error,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


class CriticAgent:
    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self._client = client or DeepSeekClient()

    def run(self, profile: BrandProfile | None = None, *, warn_threshold: float = 6.0) -> dict:
        profile = profile or load_profile()
        brief = read_json("brief.json")
        creative_brief = read_json("creative_brief.json")
        caption = read_json("caption.json")
        visual_spec = read_json("visual_spec.json")

        payload = {
            "post_type": brief.get("post_type", creative_brief.get("post_type", "general")),
            "user_request": brief.get("user_request", ""),
            "brief_directives": extract_caption_directives(creative_brief),
            "visual_directives": extract_visual_directives(creative_brief),
            "binding_gaps": creative_brief.get("binding_gaps", []),
            "approved_benchmarks": format_win_examples(
                brief.get("post_type", creative_brief.get("post_type", "general"))
            ),
            "caption": {
                "hook": caption.get("hook"),
                "body": caption.get("body"),
                "cta": caption.get("cta"),
                "alt_text": caption.get("alt_text"),
                "brief_refs": caption.get("brief_refs", {}),
            },
            "visual_spec": {
                "path": visual_spec.get("path"),
                "path_reason": visual_spec.get("path_reason"),
                "path_a_prompt": visual_spec.get("path_a_prompt"),
                "path_b_edit_prompt": visual_spec.get("path_b_edit_prompt"),
                "brief_refs": visual_spec.get("brief_refs", {}),
            },
            "brand_context": build_brand_context(profile),
        }

        try:
            result = self._client.chat_json(
                system=SYSTEM_PROMPT,
                user=json.dumps(payload, ensure_ascii=False, indent=2),
                max_tokens=1024,
                temperature=0.2,
            )
        except Exception as exc:
            record = _fallback_report(str(exc))
            write_json("critic_report.json", record)
            return record

        scores = [
            result.get("caption_score"),
            result.get("visual_score"),
            result.get("alignment_score"),
        ]
        numeric_scores = [float(score) for score in scores if isinstance(score, (int, float))]
        overall = result.get("overall_score")
        if overall is None and numeric_scores:
            overall = round(mean(numeric_scores))

        record = {
            "caption_score": result.get("caption_score"),
            "visual_score": result.get("visual_score"),
            "alignment_score": result.get("alignment_score"),
            "overall_score": overall,
            "issues": result.get("issues", [])[:3],
            "suggestions": result.get("suggestions", [])[:3],
            "summary": result.get("summary", ""),
            "low_quality_warning": isinstance(overall, (int, float)) and float(overall) < warn_threshold,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json("critic_report.json", record)
        return record

    @staticmethod
    def load_report() -> dict | None:
        return try_read_json("critic_report.json")
