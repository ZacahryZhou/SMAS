from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

from config import STATE_DIR, settings
from core.brand_context import build_brand_context
from core.job_store import mark_step_done, read_json, write_json
from core.models import BrandProfile
from core.profile_store import load_profile
from tools.deepseek_client import DeepSeekClient
from tools.fal_image import FalImageClient

PROMPT_SYSTEM = """
You are the Image Prompt Agent for SMAS.

Given topic, caption hook, and brand visual style, write one English image prompt for Instagram.

Rules:
- One sentence or two short sentences in English.
- Match visual style keywords and color palette.
- Instagram vertical image, clean composition.
- If no_text_on_image is true, explicitly include: no text, no words, no typography, no logo.
- No people unless clearly relevant to the topic.

Output valid json only:
{
  "prompt": "..."
}
""".strip()


class ImageAgent:
    def __init__(
        self,
        llm: DeepSeekClient | None = None,
        fal: FalImageClient | None = None,
    ) -> None:
        self._llm = llm or DeepSeekClient()
        self._fal = fal

    def _build_prompt(self, profile: BrandProfile, topic: dict, caption: dict) -> str:
        payload = {
            "topic": topic,
            "caption_hook": caption.get("hook", ""),
            "brand_context": build_brand_context(profile),
            "no_text_on_image": profile.visual.no_text_on_image,
        }
        result = self._llm.chat_json(
            system=PROMPT_SYSTEM,
            user=json.dumps(payload, ensure_ascii=False, indent=2),
            max_tokens=512,
            temperature=0.5,
        )
        return result["prompt"]

    def _placeholder_image(self, output_path: Path, profile: BrandProfile, prompt: str) -> None:
        color = (245, 240, 235)
        if profile.visual.color_palette:
            hex_color = profile.visual.color_palette[0].lstrip("#")
            if len(hex_color) == 6:
                color = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

        image = Image.new("RGB", (1080, 1350), color=color)
        draw = ImageDraw.Draw(image)
        draw.rectangle((80, 120, 1000, 1230), outline=(180, 180, 180), width=3)
        draw.text((100, 60), "SMAS dry-run placeholder", fill=(80, 80, 80))
        draw.text((100, 1280), prompt[:90] + ("..." if len(prompt) > 90 else ""), fill=(100, 100, 100))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)

    def run(self, profile: BrandProfile | None = None) -> dict:
        profile = profile or load_profile()
        topic = read_json("topic.json")
        caption = read_json("caption.json")
        prompt = self._build_prompt(profile, topic, caption)

        output_path = STATE_DIR / "image.png"

        if settings.fal_key:
            fal = self._fal or FalImageClient()
            meta = fal.generate_image(prompt=prompt, output_path=output_path)
            source = "fal"
        elif settings.dry_run:
            self._placeholder_image(output_path, profile, prompt)
            meta = {
                "model": "dry-run-placeholder",
                "prompt": prompt,
                "aspect_ratio": "4:5",
                "resolution": "1080x1350",
                "file": str(output_path),
                "source_url": None,
            }
            source = "dry-run"
        else:
            raise RuntimeError("FAL_KEY is required when DRY_RUN=false.")

        image_record = {
            **meta,
            "source": source,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json("image.json", image_record)
        mark_step_done("image", next_step="preview")
        return image_record
