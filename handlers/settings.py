import logging

from telegram import Update
from telegram.ext import ContextTypes

from services import database

logger = logging.getLogger(__name__)


async def pause_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    if not user_profile:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    database.update_user(telegram_id, {"notifications_paused": True})
    await update.message.reply_text(
        "Notifications paused. You won't receive daily summaries or check-in messages.\n\n"
        "Send /resume to re-enable them."
    )
    logger.info("Notifications paused for user %d", telegram_id)


async def resume_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    if not user_profile:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    database.update_user(telegram_id, {"notifications_paused": False})
    await update.message.reply_text(
        "Notifications re-enabled. You'll receive daily summaries again."
    )
    logger.info("Notifications resumed for user %d", telegram_id)
