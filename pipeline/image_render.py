#读取visual_spec.json 根据path调用fal.ai或者pillow生成真是图片输出image.png

#注意这个是 决策->执行 的分离模式 叫做关注点分离 就是决定做什么和怎么做不放在同一个地方
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

from config import STATE_DIR, settings
from core.asset_manager import resolve_asset_path
from core.brand_context import build_brand_context
from core.job_store import mark_step_done, read_json, try_read_json, write_json
from core.models import BrandProfile
from core.profile_store import load_profile
from pipeline.template_composer import compose_template_image
from tools.deepseek_client import DeepSeekClient
from tools.fal_image import FalImageClient

PATH_A_PROMPT_SYSTEM = """
You are the Image Prompt Agent for SMAS.

Write one English image prompt for Instagram Path A generation.

Rules:
- One or two short sentences in English.
- Use the scene and color mood from the payload.
- Instagram vertical image, clean composition.
- Include: no text, no words, no typography, no logo.
- No people unless clearly relevant.

Output valid json only:
{
  "prompt": "..."
}
""".strip()

PATH_B_PROMPT_SYSTEM = """
You are the Image Edit Prompt Agent for SMAS Path B.

The model receives the user's product photo as a reference image.
Write one English edit prompt that places the product naturally in an Instagram lifestyle scene.

Rules:
- Mention the reference product as the hero subject in the scene.
- Use creative_brief.visual.scene and color_mood.
- Realistic photo style, vertical 4:5 composition.
- No text, no words, no typography, no logo in the image.
- Do not change the product into a different item.

Output valid json only:
{
  "prompt": "..."
}
""".strip()


class ImageRenderPipeline:
    def __init__(
        self,
        llm: DeepSeekClient | None = None,
        fal: FalImageClient | None = None,
    ) -> None:
        self._llm = llm or DeepSeekClient()
        self._fal = fal

#这便是根据上一步的visual_director决定的path然后根据A/B/C不同的路径来生成图片
    def run(self, profile: BrandProfile | None = None) -> dict:
        profile = profile or load_profile()
        visual_spec = read_json("visual_spec.json")
        path = visual_spec.get("path", "A").upper()

        if path == "C":
            record = self._render_path_c(visual_spec, profile)
        elif path == "B":
            record = self._render_path_b(visual_spec, profile)
        elif path == "A":
            record = self._render_path_a(visual_spec, profile)
        else:
            raise RuntimeError(f"Unsupported render path: {path}")

        write_json("image.json", record)
        mark_step_done("image", next_step="preview")
        return record

    def _render_path_a(self, visual_spec: dict, profile: BrandProfile) -> dict:
        output_path = STATE_DIR / "image.png"
        prompt = visual_spec.get("path_a_prompt") or self._build_path_a_prompt(visual_spec, profile)
#这里的是dry——run测试如果有api可以调用API但是如果没有api key的时候则可以调用假图来占位
        if settings.fal_key and not settings.dry_run:
            fal = self._fal or FalImageClient()
            meta = fal.generate_image(prompt=prompt, output_path=output_path)
            source = "fal"
        elif settings.dry_run:
            meta = self._placeholder_meta(output_path, profile, prompt, label="Path A dry-run")
            source = "dry-run"
        else:
            raise RuntimeError("FAL_KEY is required when DRY_RUN=false.")

        return {
            **meta,
            "source": source,
            "render_path": "A",
            "post_type": visual_spec.get("post_type", "general"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def _render_path_b(self, visual_spec: dict, profile: BrandProfile) -> dict:
        output_path = STATE_DIR / "image.png"
        prompt = visual_spec.get("path_b_edit_prompt") or self._build_path_b_prompt(visual_spec, profile)
        reference_paths = self._resolve_reference_paths(visual_spec)

        if settings.fal_key and not settings.dry_run:
            fal = self._fal or FalImageClient()
            meta = fal.edit_image(
                prompt=prompt,
                image_paths=reference_paths,
                output_path=output_path,
            )
            source = "fal-edit"
        elif settings.dry_run:
            meta = self._render_path_b_dry_run(
                visual_spec,
                profile,
                output_path=output_path,
                prompt=prompt,
                reference_paths=reference_paths,
            )
            source = "dry-run"
        else:
            raise RuntimeError("FAL_KEY is required when DRY_RUN=false.")

        return {
            **meta,
            "source": source,
            "render_path": "B",
            "post_type": visual_spec.get("post_type", "general"),
            "reference_images": [str(path) for path in reference_paths],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def _render_path_c(self, visual_spec: dict, profile: BrandProfile) -> dict:
        output_path = STATE_DIR / "image.png"
        background_image = None

        if visual_spec.get("path_c_use_ai_background") and settings.fal_key and not settings.dry_run:
            prompt = visual_spec.get("path_a_prompt") or self._build_path_a_prompt(visual_spec, profile)
            temp_bg = STATE_DIR / "image_bg.png"
            fal = self._fal or FalImageClient()
            fal.generate_image(prompt=prompt, output_path=temp_bg)
            background_image = Image.open(temp_bg).convert("RGBA")

        compose_template_image(
            visual_spec=visual_spec,
            profile=profile,
            output_path=output_path,
            background_image=background_image,
        )

        return {
            "model": "template-composer",
            "render_path": "C",
            "template": visual_spec.get("path_c_template", "event_hero_v1"),
            "file": str(output_path),
            "assets_used": visual_spec.get("assets_used", []),
            "text_overlay": visual_spec.get("text_overlay", {}),
            "aspect_ratio": "4:5",
            "resolution": "1080x1350",
            "source": "template",
            "post_type": visual_spec.get("post_type", "general"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def _resolve_reference_paths(self, visual_spec: dict) -> list[Path]:
        paths: list[Path] = []
        for asset in visual_spec.get("assets_used", []):
            if asset.get("role") == "hero_product":
                paths.append(resolve_asset_path(asset["path"]))
        if not paths:
            raise RuntimeError("Path B requires a hero_product asset in visual_spec.assets_used")
        return paths

    def _render_path_b_dry_run(
        self,
        visual_spec: dict,
        profile: BrandProfile,
        *,
        output_path: Path,
        prompt: str,
        reference_paths: list[Path],
    ) -> dict:
        dry_spec = {
            **visual_spec,
            "text_overlay": {"enabled": False, "lines": []},
        }
        compose_template_image(
            visual_spec=dry_spec,
            profile=profile,
            output_path=output_path,
            background_image=None,
        )

        image = Image.open(output_path)
        draw = ImageDraw.Draw(image)
        draw.text((80, 40), "Path B dry-run (local composite)", fill=(90, 90, 90))
        image.save(output_path)

        return {
            "model": "path-b-dry-run",
            "prompt": prompt,
            "aspect_ratio": "4:5",
            "resolution": "1080x1350",
            "file": str(output_path),
            "source_url": None,
            "reference_images": [str(path) for path in reference_paths],
        }

    def _build_path_a_prompt(self, visual_spec: dict, profile: BrandProfile) -> str:
        creative_brief = try_read_json("creative_brief.json") or {}
        caption = try_read_json("caption.json") or {}
        payload = {
            "visual_spec": visual_spec,
            "creative_brief": creative_brief,
            "caption_hook": caption.get("hook", ""),
            "brand_context": build_brand_context(profile),
        }
        result = self._llm.chat_json(
            system=PATH_A_PROMPT_SYSTEM,
            user=json.dumps(payload, ensure_ascii=False, indent=2),
            max_tokens=512,
            temperature=0.4,
        )
        return result["prompt"]

    def _build_path_b_prompt(self, visual_spec: dict, profile: BrandProfile) -> str:
        creative_brief = try_read_json("creative_brief.json") or {}
        caption = try_read_json("caption.json") or {}
        payload = {
            "visual_spec": visual_spec,
            "creative_brief": creative_brief,
            "caption_hook": caption.get("hook", ""),
            "assets_used": visual_spec.get("assets_used", []),
            "brand_context": build_brand_context(profile),
        }
        result = self._llm.chat_json(
            system=PATH_B_PROMPT_SYSTEM,
            user=json.dumps(payload, ensure_ascii=False, indent=2),
            max_tokens=512,
            temperature=0.4,
        )
        return result["prompt"]

    def _placeholder_meta(
        self,
        output_path: Path,
        profile: BrandProfile,
        prompt: str,
        *,
        label: str = "SMAS dry-run placeholder",
    ) -> dict:
        color = (245, 240, 235)
        if profile.visual.color_palette:
            hex_color = profile.visual.color_palette[0].lstrip("#")
            if len(hex_color) == 6:
                color = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

        image = Image.new("RGB", (1080, 1350), color=color)
        draw = ImageDraw.Draw(image)
        draw.rectangle((80, 120, 1000, 1230), outline=(180, 180, 180), width=3)
        draw.text((100, 60), label, fill=(80, 80, 80))
        draw.text((100, 1280), prompt[:90] + ("..." if len(prompt) > 90 else ""), fill=(100, 100, 100))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)

        return {
            "model": "dry-run-placeholder",
            "prompt": prompt,
            "aspect_ratio": "4:5",
            "resolution": "1080x1350",
            "file": str(output_path),
            "source_url": None,
        }
