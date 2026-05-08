import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from services import ai, database

logger = logging.getLogger(__name__)

_EATING_PATTERN = re.compile(
    r"eating out at\s+(.+?)(?:[.!?]|$)|going to\s+(.+?)(?:[.!?]|$)",
    re.IGNORECASE,
)


def _extract_restaurant(text: str) -> str:
    m = _EATING_PATTERN.search(text)
    if m:
        return (m.group(1) or m.group(2)).strip()
    return "this restaurant"


async def restaurant_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    if not user_profile:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    text = update.message.text or ""

    if context.args:
        restaurant_type = " ".join(context.args)
    else:
        restaurant_type = _extract_restaurant(text)

    today_calories = database.get_today_calories(telegram_id)
    calorie_target = user_profile.get("calorie_target") or 2000
    remaining = max(0, calorie_target - today_calories)
    diet = user_profile.get("diet_preference") or "none"

    user_message = (
        f"I'm eating at {restaurant_type}. "
        f"I have {remaining} kcal remaining today. "
        f"My diet preference is {diet}. "
        "Give me: 3 safe choices with kcal, 2 items to avoid with reason, 1 ordering hack. "
        "Keep total response under 100 words."
    )

    await update.message.reply_text("Checking options for you...")
    response = ai.chat_response(user_message, user_profile)
    await update.message.reply_text(response)
    logger.info("Restaurant advice for user %d at '%s'", telegram_id, restaurant_type)
