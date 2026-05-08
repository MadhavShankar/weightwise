import logging

from telegram import Update
from telegram.ext import ContextTypes

from services import ai, database

logger = logging.getLogger(__name__)


def _water_goal_ml(user_profile: dict) -> int:
    stored = user_profile.get("water_goal_ml")
    if stored:
        return int(stored)
    weight = user_profile.get("weight_kg") or 0
    if not weight:
        return 2500
    activity = (user_profile.get("activity_level") or "").lower()
    if any(w in activity for w in ("very active", "highly active", "athlete")):
        ml_per_kg = 40
    elif any(w in activity for w in ("active", "moderate")):
        ml_per_kg = 35
    else:
        ml_per_kg = 30
    return int(weight * ml_per_kg)


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
    goal = _water_goal_ml(user_profile)
    name = user_profile.get("name", "")

    if total_ml >= goal:
        nudge = f"Excellent, {name} — you've hit your {goal}ml water goal for today."
    elif total_ml >= goal * 0.6:
        remaining = goal - total_ml
        nudge = f"Good progress, {name}. {remaining}ml more to hit your {goal}ml goal."
    else:
        remaining = goal - total_ml
        nudge = f"Keep going, {name} — {remaining}ml still to go to reach your {goal}ml goal."

    await update.message.reply_text(
        f"Logged {amount_ml}ml. Total today: {total_litres:.1f}L\n\n{nudge}"
    )
    logger.info("Logged water for user %d: %dml (total today: %dml)", telegram_id, amount_ml, total_ml)
