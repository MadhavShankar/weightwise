import logging

from telegram import Update
from telegram.ext import ContextTypes

from services import ai, database

logger = logging.getLogger(__name__)


async def water_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    if not user_profile:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    if context.args:
        description = " ".join(context.args)
    else:
        description = update.message.text or ""

    if not description:
        await update.message.reply_text("Usage: /water <amount> (e.g. '2 glasses', '500ml', '1 litre')")
        return

    amount_ml = ai.analyze_water(description)
    database.log_water(telegram_id=telegram_id, amount_ml=amount_ml)

    total_ml = database.get_today_water_ml(telegram_id)
    total_litres = total_ml / 1000

    name = user_profile.get("name", "")
    if total_ml >= 2500:
        nudge = f"Excellent hydration, {name} — you've hit your daily goal!"
    elif total_ml >= 1500:
        remaining = 2500 - total_ml
        nudge = f"Good going, {name}. {remaining}ml more to hit 2.5L today."
    else:
        remaining = 2500 - total_ml
        nudge = f"Keep drinking, {name} — {remaining}ml still to go to reach 2.5L."

    await update.message.reply_text(
        f"Logged {amount_ml}ml. Total today: {total_litres:.1f}L\n\n{nudge}"
    )
    logger.info("Logged water for user %d: %dml (total today: %dml)", telegram_id, amount_ml, total_ml)
