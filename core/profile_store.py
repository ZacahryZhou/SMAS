from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import PROFILE_HISTORY_DIR, PROFILE_PATH, ensure_dirs
from core.models import BrandProfile


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_profile() -> BrandProfile:
    ensure_dirs()
    if not PROFILE_PATH.exists():
        profile = BrandProfile()
        save_profile(profile)
        return profile

    data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    return BrandProfile.model_validate(data)


def save_profile(profile: BrandProfile) -> BrandProfile:
    ensure_dirs()
    profile.updated_at = datetime.now(timezone.utc).isoformat()
    PROFILE_PATH.write_text(
        json.dumps(profile.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return profile


def backup_profile(profile: BrandProfile) -> Path:
    ensure_dirs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_path = PROFILE_HISTORY_DIR / f"brand_profile-{stamp}.json"
    backup_path.write_text(
        json.dumps(profile.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return backup_path


def apply_patch(profile: BrandProfile, patch: dict[str, Any]) -> BrandProfile:
    if not patch:
        return profile

    backup_profile(profile)
    merged = _deep_merge(profile.model_dump(), patch)
    updated = BrandProfile.model_validate(merged)
    return save_profile(updated)


def reset_profile() -> BrandProfile:
    ensure_dirs()
    if PROFILE_PATH.exists():
        backup_profile(load_profile())
        PROFILE_PATH.unlink()
    return save_profile(BrandProfile())
