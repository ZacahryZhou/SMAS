from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import STATE_DIR
from core.job_store import mark_step_done, read_json, write_json
from core.models import BrandProfile
from core.profile_store import load_profile

CANVAS_WIDTH = 1080
HEADER_HEIGHT = 72
IMAGE_HEIGHT = 1350
FOOTER_HEIGHT = 320
CANVAS_HEIGHT = HEADER_HEIGHT + IMAGE_HEIGHT + FOOTER_HEIGHT


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/Library/Fonts/Arial Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
        )

    for path in candidates:
        font_path = Path(path)
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default()


def _fit_cover(image: Image.Image, width: int, height: int) -> Image.Image:
    src_w, src_h = image.size
    scale = max(width / src_w, height / src_h)
    resized = image.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def _wrap_text(text: str, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines():
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        lines.extend(textwrap.wrap(paragraph, width=width) or [""])
    return lines


def compose_instagram_preview(
    *,
    image_path: Path,
    caption: dict,
    profile: BrandProfile,
    output_path: Path,
) -> Path:
    canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), color=(255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    title_font = _load_font(28, bold=True)
    body_font = _load_font(24)
    small_font = _load_font(20)
    icon_font = _load_font(28)

    handle = profile.account.handle or "username"
    display_name = profile.account.display_name or handle

    draw.ellipse((32, 20, 72, 60), fill=(220, 220, 220))
    draw.text((88, 24), handle, fill=(20, 20, 20), font=title_font)
    draw.text((980, 28), "•••", fill=(80, 80, 80), font=body_font)

    source = Image.open(image_path).convert("RGB")
    fitted = _fit_cover(source, CANVAS_WIDTH, IMAGE_HEIGHT)
    canvas.paste(fitted, (0, HEADER_HEIGHT))

    footer_top = HEADER_HEIGHT + IMAGE_HEIGHT + 24
    draw.text((32, footer_top), "♡   💬   ✈   🔖", fill=(30, 30, 30), font=icon_font)

    text_top = footer_top + 48
    draw.text((32, text_top), handle, fill=(20, 20, 20), font=title_font)

    hook = caption.get("hook", "").strip()
    body = caption.get("body", "").strip()
    preview_body = f"{hook}\n{body}" if body else hook
    lines = _wrap_text(preview_body, width=48)[:4]
    if len(_wrap_text(preview_body, width=48)) > 4:
        lines[-1] = lines[-1].rstrip(".") + "... more"

    y = text_top + 40
    for line in lines:
        draw.text((32, y), line, fill=(30, 30, 30), font=body_font)
        y += 30

    hashtags = caption.get("hashtags", [])
    if hashtags:
        tag_line = " ".join(hashtags[:6])
        if len(hashtags) > 6:
            tag_line += " ..."
        draw.text((32, y + 12), tag_line, fill=(120, 120, 120), font=small_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)

    meta = {
        "file": str(output_path),
        "width": CANVAS_WIDTH,
        "height": CANVAS_HEIGHT,
        "display_name": display_name,
        "handle": handle,
        "composed_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json("preview_feed.json", meta)
    return output_path


class PreviewComposer:
    def run(self, profile: BrandProfile | None = None) -> Path:
        profile = profile or load_profile()
        caption = read_json("caption.json")
        image_path = STATE_DIR / "image.png"
        if not image_path.exists():
            raise FileNotFoundError(f"Missing image file: {image_path}")

        output_path = STATE_DIR / "preview_feed.png"
        compose_instagram_preview(
            image_path=image_path,
            caption=caption,
            profile=profile,
            output_path=output_path,
        )
        mark_step_done("preview", next_step="review", status="waiting_review")
        return output_path
