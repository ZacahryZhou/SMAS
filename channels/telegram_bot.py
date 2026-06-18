from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from config import settings
from core.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


def _authorized(update: Update) -> bool:
    if not settings.telegram_chat_id:
        return True
    if not update.effective_chat:
        return False
    return str(update.effective_chat.id) == str(settings.telegram_chat_id).strip()


async def _reject_unauthorized(update: Update) -> None:
    if update.message:
        await update.message.reply_text("This bot is not authorized for the current chat.")


async def _run_orchestrator(text: str):
    orchestrator = Orchestrator()
    return await asyncio.to_thread(orchestrator.handle_text, text)


async def _reply_result(update: Update, result) -> None:
    if not update.message:
        return
    if result.image_path:
        with result.image_path.open("rb") as image_file:
            await update.message.reply_photo(photo=image_file, caption=result.text[:1024])
    else:
        await update.message.reply_text(result.text)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        await _reject_unauthorized(update)
        return
    result = await _run_orchestrator("/start")
    await _reply_result(update, result)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        await _reject_unauthorized(update)
        return
    result = await _run_orchestrator("/help")
    await _reply_result(update, result)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        await _reject_unauthorized(update)
        return
    result = await _run_orchestrator("/status")
    await _reply_result(update, result)


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        await _reject_unauthorized(update)
        return
    result = await _run_orchestrator("/profile")
    await _reply_result(update, result)


async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        await _reject_unauthorized(update)
        return
    if not update.message:
        return

    request = " ".join(context.args).strip()
    if not request:
        await update.message.reply_text("Usage: /generate Create a post about AI agents")
        return

    await update.message.reply_text("Generating... this usually takes 30-90 seconds.")
    try:
        result = await _run_orchestrator(f"/generate {request}")
    except Exception as exc:
        logger.exception("generate failed")
        await update.message.reply_text(f"Generation failed: {exc}")
        return
    await _reply_result(update, result)


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        await _reject_unauthorized(update)
        return
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    if not text:
        return

    state_hint = text.lower()
    if any(
        word in state_hint
        for word in (
            "做一条",
            "生成",
            "发帖",
            "generate",
            "create a post",
            "make a post",
            "write a post",
        )
    ):
        await update.message.reply_text("Generating... this usually takes 30-90 seconds.")

    try:
        result = await _run_orchestrator(text)
    except Exception as exc:
        logger.exception("message handling failed")
        await update.message.reply_text(f"Request failed: {exc}")
        return

    await _reply_result(update, result)


def validate_telegram_config() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing in .env")
    if not settings.telegram_chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID is missing in .env")


def run_bot() -> None:
    validate_telegram_config()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("generate", generate_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))

    logger.info("SMAS Telegram bot started. Waiting for messages...")
    app.run_polling(drop_pending_updates=True)
