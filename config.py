from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
STATE_DIR = ROOT_DIR / "state"
PROFILE_HISTORY_DIR = DATA_DIR / "profile_history"

PROFILE_PATH = DATA_DIR / "brand_profile.json"
DATABASE_PATH = DATA_DIR / "smas.db"

load_dotenv(ROOT_DIR / ".env")


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    dry_run: bool = _bool(os.getenv("DRY_RUN"), default=True)

    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    fal_key: str = os.getenv("FAL_KEY", "")

    # product_promo + assets: auto | b (reference gen) | c (template)
    product_render_path: str = os.getenv("SMAS_PRODUCT_RENDER_PATH", "auto").strip().lower()

    type_confirm_threshold: float = float(os.getenv("SMAS_TYPE_CONFIRM_THRESHOLD", "0.8"))

    critic_enabled: bool = _bool(os.getenv("SMAS_CRITIC_ENABLED"), default=True)
    critic_warn_threshold: float = float(os.getenv("SMAS_CRITIC_WARN_THRESHOLD", "6"))

    wins_example_limit: int = int(os.getenv("SMAS_WINS_EXAMPLE_LIMIT", "2"))
    wins_min_score: float = float(os.getenv("SMAS_WINS_MIN_SCORE", "0"))

    ssl_verify: bool = _bool(os.getenv("SMAS_SSL_VERIFY"), default=True)
    ssl_cert_file: str = os.getenv("SSL_CERT_FILE", "")

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

    database_path: Path = Path(os.getenv("DATABASE_PATH", str(DATABASE_PATH)))


settings = Settings()


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    from core.feedback_store import ensure_feedback_dirs
    from core.playbook import ensure_playbook_dirs

    ensure_playbook_dirs()
    ensure_feedback_dirs()
