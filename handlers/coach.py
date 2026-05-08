import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from services import ai, database

logger = logging.getLogger(__name__)

_INTENT_RE = re.compile(r"^INTENT:\s*(meal|chat)", re.IGNORECASE | re.MULTILINE)
_CALORIES_RE = re.compile(r"Calories:\s*(\d+)")


async def coach_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    if not user_profile:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    message = update.message.text or ""

    today_calories = database.get_today_calories(telegram_id)
    exercise_calories = database.get_today_exercise_calories(telegram_id)
    water_ml = database.get_today_water_ml(telegram_id)

    profile_with_today = {
        **user_profile,
        "today_calories": today_calories,
        "exercise_calories": exercise_calories,
        "water_ml": water_ml,
    }

    response = ai.coach_chat(message, profile_with_today)

    intent_match = _INTENT_RE.search(response)
    intent = intent_match.group(1).lower() if intent_match else "chat"

    if intent == "meal":
        cal_match = _CALORIES_RE.search(response)
        calories = int(cal_match.group(1)) if cal_match else 0

        meal_id = database.log_meal(
            telegram_id=telegram_id,
            description=message,
            calories=calories,
            meal_data={"ai_response": response, "calories": calories},
        )

        context.user_data["last_meal_id"] = meal_id
        context.user_data["last_meal_analysis"] = response
        context.user_data["last_meal_today_calories"] = today_calories

        clean_response = _INTENT_RE.sub("", response).strip()
        await update.message.reply_text(
            f"{clean_response}\n\nPortion size wrong? Just reply with the correction."
        )
        logger.info("Coach routed meal for user %d: %d kcal", telegram_id, calories)
    else:
        clean_response = _INTENT_RE.sub("", response).strip()
        await update.message.reply_text(clean_response)
        logger.info("Coach chat for user %d", telegram_id)
