from __future__ import annotations

from pathlib import Path

from config import DATA_DIR, ensure_dirs

ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
PRODUCTS_DIR = DATA_DIR / "assets" / "products"
LOGOS_DIR = DATA_DIR / "assets" / "logos"


def ensure_asset_dirs() -> None:
    ensure_dirs()
    PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)


def list_asset_paths(directory: Path) -> list[str]:
    if not directory.exists():
        return []
    paths: list[str] = []
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix.lower() in ASSET_EXTENSIONS:
            paths.append(str(path.relative_to(DATA_DIR)))
    return paths


def list_available_assets() -> dict[str, list[str]]:
    ensure_asset_dirs()
    return {
        "products": list_asset_paths(PRODUCTS_DIR),
        "logos": list_asset_paths(LOGOS_DIR),
    }


def flatten_available_assets() -> list[str]:
    assets = list_available_assets()
    return assets["products"] + assets["logos"]
