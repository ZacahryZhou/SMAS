from __future__ import annotations

from pathlib import Path

from PIL import Image

from config import DATA_DIR
from core.asset_store import ASSET_EXTENSIONS, PRODUCTS_DIR, ensure_asset_dirs

try:
    from rembg import remove as rembg_remove
except ImportError:  # pragma: no cover - optional dependency
    rembg_remove = None


class AssetError(RuntimeError):
    pass


def resolve_asset_path(relative_path: str) -> Path:
    ensure_asset_dirs()
    path = (DATA_DIR / relative_path).resolve()
    data_root = DATA_DIR.resolve()
    if data_root not in path.parents and path != data_root:
        raise AssetError(f"Asset path escapes data directory: {relative_path}")
    if not path.exists() or not path.is_file():
        raise AssetError(f"Asset not found: {relative_path}")
    if path.suffix.lower() not in ASSET_EXTENSIONS:
        raise AssetError(f"Unsupported asset type: {relative_path}")
    return path


def pick_default_product(assets_available: list[str]) -> str | None:
    products = [path for path in assets_available if path.startswith("assets/products/")]
    if products:
        return products[0]
    return assets_available[0] if assets_available else None


def prepare_product_image(path: Path, *, needs_cutout: bool = True) -> Image.Image:
    image = Image.open(path)
    if image.mode == "RGBA":
        rgba = image
    else:
        rgba = image.convert("RGBA")

    from pipeline.image_utils import has_transparency

    if needs_cutout and not has_transparency(rgba) and rembg_remove is not None:
        rgba = rembg_remove(rgba)
        if isinstance(rgba, bytes):
            from io import BytesIO

            rgba = Image.open(BytesIO(rgba)).convert("RGBA")
        elif rgba.mode != "RGBA":
            rgba = rgba.convert("RGBA")

    return rgba


def load_product_asset(relative_path: str, *, needs_cutout: bool = True) -> Image.Image:
    return prepare_product_image(resolve_asset_path(relative_path), needs_cutout=needs_cutout)


def list_product_assets() -> list[str]:
    ensure_asset_dirs()
    if not PRODUCTS_DIR.exists():
        return []
    return [
        str(path.relative_to(DATA_DIR))
        for path in sorted(PRODUCTS_DIR.iterdir())
        if path.is_file() and path.suffix.lower() in ASSET_EXTENSIONS
    ]
