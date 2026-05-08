import logging

from telegram import Update
from telegram.ext import ContextTypes

from services import ai, database

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = (
    "name", "age", "gender", "height_cm",
    "weight_kg", "target_weight_kg", "activity_level", "calorie_target",
)


async def plan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    if not user_profile:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    missing = [f for f in _REQUIRED_FIELDS if not user_profile.get(f)]
    if missing:
        await update.message.reply_text(
            "Your profile is incomplete. Please finish onboarding with /start before generating a plan."
        )
        return

    await update.message.reply_text("Generating your personalised weight plan...")

    plan = ai.generate_weight_plan(user_profile)
    database.update_user(telegram_id, {"current_plan": plan})

    await update.message.reply_text(plan)
    logger.info("Generated weight plan for user %d", telegram_id)
