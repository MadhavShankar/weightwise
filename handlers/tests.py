import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from services import ai, database

logger = logging.getLogger(__name__)

_PLATEAU_WEEKS = 4
_PLATEAU_THRESHOLD_KG_PER_WEEK = 0.3


def _compute_plateau(weight_history: list) -> tuple[float, bool]:
    """Returns (kg_per_week, is_plateau). Positive = weight lost."""
    if len(weight_history) < 2:
        return 0.0, False
    first = weight_history[0]
    last = weight_history[-1]
    first_date = datetime.fromisoformat(first["logged_at"])
    last_date = datetime.fromisoformat(last["logged_at"])
    weeks = max((last_date - first_date).total_seconds() / (7 * 86400), 1)
    rate = round((first["weight_kg"] - last["weight_kg"]) / weeks, 2)
    return rate, rate < _PLATEAU_THRESHOLD_KG_PER_WEEK


async def tests_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    if not user_profile:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    weight_history = database.get_weight_history(telegram_id, days=_PLATEAU_WEEKS * 7)
    weight_loss_rate, plateau_flag = _compute_plateau(weight_history)

    last_report = database.get_last_report_summary(telegram_id)

    profile = {
        **user_profile,
        "weight_loss_rate": weight_loss_rate,
        "plateau_flag": plateau_flag,
        "last_report_markers": last_report or "none",
    }

    await update.message.reply_text("Generating your personalised test recommendations...")

    response = ai.recommend_lab_tests(profile)
    await update.message.reply_text(response)
    logger.info(
        "Test recommendations sent to user %d (rate=%.2f kg/wk, plateau=%s)",
        telegram_id, weight_loss_rate, plateau_flag,
    )
