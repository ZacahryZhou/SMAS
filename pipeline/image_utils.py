from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFont

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1350

FONT_SIZE = {"small": 36, "medium": 52, "large": 76}


def load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates: list[str] = []
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

    for candidate in candidates:
        font_path = Path(candidate)
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default()


def hex_to_rgb(value: str, fallback: tuple[int, int, int] = (245, 240, 235)) -> tuple[int, int, int]:
    cleaned = value.strip().lstrip("#")
    if len(cleaned) != 6:
        return fallback
    try:
        return tuple(int(cleaned[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return fallback


def has_transparency(image: Image.Image) -> bool:
    if image.mode != "RGBA":
        return False
    alpha = image.getchannel("A")
    extrema = alpha.getextrema()
    return extrema[0] < 255


def paste_rgba(base: Image.Image, overlay: Image.Image, position: tuple[int, int]) -> None:
    if overlay.mode != "RGBA":
        overlay = overlay.convert("RGBA")
    base.paste(overlay, position, overlay)
