from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from core.asset_manager import load_product_asset
from core.models import BrandProfile
from pipeline.image_utils import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    FONT_SIZE,
    hex_to_rgb,
    load_font,
    paste_rgba,
)


def _zone_position(zone: str, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> tuple[int, int]:
    bbox = font.getbbox(text)
    text_w = bbox[2] - bbox[0]
    margin = 64
    if zone == "top-left":
        return margin, margin
    if zone == "top-center":
        return (CANVAS_WIDTH - text_w) // 2, margin
    if zone == "bottom-left":
        return margin, CANVAS_HEIGHT - margin - (bbox[3] - bbox[1])
    if zone == "bottom-center":
        return (CANVAS_WIDTH - text_w) // 2, CANVAS_HEIGHT - margin - (bbox[3] - bbox[1])
    return margin, margin


def _draw_background(canvas: Image.Image, background: str, accent: str) -> None:
    draw = ImageDraw.Draw(canvas)
    base = hex_to_rgb(background)
    accent_rgb = hex_to_rgb(accent, fallback=(232, 93, 76))
    draw.rectangle((0, 0, CANVAS_WIDTH, CANVAS_HEIGHT), fill=base)
    draw.ellipse((-120, 900, 520, 1500), fill=accent_rgb + (40,) if len(accent_rgb) == 3 else accent_rgb)
    draw.rectangle((0, 0, CANVAS_WIDTH, 18), fill=accent_rgb)


def _paste_product(
    canvas: Image.Image,
    asset_path: str,
    position: list[float],
    *,
    needs_cutout: bool,
) -> None:
    product = load_product_asset(asset_path, needs_cutout=needs_cutout)
    max_w = int(CANVAS_WIDTH * 0.62)
    max_h = int(CANVAS_HEIGHT * 0.55)
    product.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

    anchor_x = int(position[0] * CANVAS_WIDTH) - product.width // 2
    anchor_y = int(position[1] * CANVAS_HEIGHT) - product.height // 2
    anchor_x = max(40, min(anchor_x, CANVAS_WIDTH - product.width - 40))
    anchor_y = max(120, min(anchor_y, CANVAS_HEIGHT - product.height - 160))
    paste_rgba(canvas, product, (anchor_x, anchor_y))


def compose_template_image(
    *,
    visual_spec: dict,
    profile: BrandProfile,
    output_path: Path,
    background_image: Image.Image | None = None,
) -> Path:
    color = visual_spec.get("color", {})
    background = color.get("background") or (
        profile.visual.color_palette[0] if profile.visual.color_palette else "#F5F0EB"
    )
    accent = color.get("accent", "#E85D4C")

    if background_image is not None:
        canvas = background_image.convert("RGBA").resize((CANVAS_WIDTH, CANVAS_HEIGHT), Image.Resampling.LANCZOS)
    else:
        canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT))
        _draw_background(canvas, background, accent)

    composition = visual_spec.get("composition", {})
    product_position = composition.get("product_position", [0.55, 0.5])

    for asset in visual_spec.get("assets_used", []):
        if asset.get("role") == "hero_product":
            _paste_product(
                canvas,
                asset["path"],
                product_position,
                needs_cutout=bool(asset.get("needs_cutout", True)),
            )

    overlay = visual_spec.get("text_overlay", {})
    if overlay.get("enabled"):
        draw = ImageDraw.Draw(canvas)
        accent_rgb = hex_to_rgb(accent)
        for line in overlay.get("lines", []):
            text = str(line.get("text", "")).strip()
            if not text:
                continue
            size_key = line.get("size", "medium")
            font_size = FONT_SIZE.get(size_key, FONT_SIZE["medium"])
            font = load_font(font_size, bold=size_key == "large")
            x, y = _zone_position(line.get("zone", "top-left"), text, font)
            draw.text((x + 2, y + 2), text, fill=(0, 0, 0, 80), font=font)
            draw.text((x, y), text, fill=accent_rgb, font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path)
    return output_path
