from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import fal_client as fal_sdk

from config import settings
from tools.http_download import download_file


class FalError(RuntimeError):
    pass


class FalImageClient:
    def __init__(self) -> None:
        if not settings.fal_key:
            raise FalError("FAL_KEY is missing. Copy .env.example to .env and add your key.")
        os.environ["FAL_KEY"] = settings.fal_key

    def generate_image(
        self,
        *,
        prompt: str,
        output_path: Path,
        aspect_ratio: str = "4:5",
        resolution: str = "1K",
        enable_web_search: bool = False,
    ) -> dict[str, Any]:
        result = fal_sdk.subscribe(
            "fal-ai/nano-banana-pro",
            arguments={
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
                "enable_web_search": enable_web_search,
            },
            with_logs=True,
        )

        images = result.get("images") or []
        if not images:
            raise FalError(f"fal.ai returned no images: {result}")

        image_url = images[0].get("url")
        if not image_url:
            raise FalError(f"fal.ai image payload missing url: {images[0]}")

        download_file(image_url, output_path)

        return {
            "model": "fal-ai/nano-banana-pro",
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "file": str(output_path),
            "source_url": image_url,
        }
