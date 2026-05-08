import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from services import ai, database

logger = logging.getLogger(__name__)

_CALORIES_RE = re.compile(r"Calories:\s*(\d+)")


def _parse_calories(response: str) -> int:
    match = _CALORIES_RE.search(response)
    if match:
        return int(match.group(1))
    logger.warning("Could not parse calories from AI response")
    return 0


async def photo_meal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    if not user_profile:
        await update.message.reply_text(
            "Please run /start first to set up your profile."
        )
        return

    photo_file = await update.message.photo[-1].get_file()
    image_bytes = bytes(await photo_file.download_as_bytearray())

    today_calories = database.get_today_calories(telegram_id)
    profile_with_today = {**user_profile, "today_calories": today_calories}

    await update.message.reply_text("Analyzing your meal...")

    response = ai.analyze_meal_photo(image_bytes, profile_with_today)

    calories = _parse_calories(response)
    database.log_meal(
        telegram_id=telegram_id,
        description=update.message.caption or "Photo meal",
        calories=calories,
        meal_data={"ai_response": response, "calories": calories},
    )

    await update.message.reply_text(response)
    logger.info("Logged meal for user %d: %d kcal", telegram_id, calories)


async def log_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    if not user_profile:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    description = update.message.text or ""
    if not description:
        return

    today_calories = database.get_today_calories(telegram_id)
    profile_with_today = {**user_profile, "today_calories": today_calories}

    response = ai.analyze_meal_text(description, profile_with_today)

    calories = _parse_calories(response)
    database.log_meal(
        telegram_id=telegram_id,
        description=description,
        calories=calories,
        meal_data={"ai_response": response, "calories": calories},
    )

    await update.message.reply_text(response)
    logger.info("Logged text meal for user %d: %d kcal", telegram_id, calories)


async def log_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    if not user_profile:
        await update.message.reply_text(
            "Please run /start first to set up your profile."
        )
        return

    description = " ".join(context.args) if context.args else ""
    if not description:
        await update.message.reply_text(
            "Usage: /log <meal description>"
        )
        return

    today_calories = database.get_today_calories(telegram_id)
    profile_with_today = {**user_profile, "today_calories": today_calories}

    response = ai.analyze_meal_text(description, profile_with_today)

    calories = _parse_calories(response)
    database.log_meal(
        telegram_id=telegram_id,
        description=description,
        calories=calories,
        meal_data={"ai_response": response, "calories": calories},
    )

    await update.message.reply_text(response)
    logger.info("Logged text meal for user %d: %d kcal", telegram_id, calories)
