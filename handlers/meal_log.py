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
    meal_id = database.log_meal(
        telegram_id=telegram_id,
        description=update.message.caption or "Photo meal",
        calories=calories,
        meal_data={"ai_response": response, "calories": calories},
    )

    context.user_data["last_meal_id"] = meal_id
    context.user_data["last_meal_analysis"] = response
    context.user_data["last_meal_today_calories"] = today_calories

    await update.message.reply_text(
        f"{response}\n\nPortion size wrong? Just reply with the correction (e.g. 'actually 2 cups of rice, not 1')."
    )
    logger.info("Logged meal for user %d: %d kcal", telegram_id, calories)


async def meal_correction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    if not user_profile:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    correction = update.message.text or ""
    meal_id = context.user_data.pop("last_meal_id", None)
    original_analysis = context.user_data.pop("last_meal_analysis", "")
    today_calories = context.user_data.pop("last_meal_today_calories", 0)

    profile_with_today = {**user_profile, "today_calories": today_calories}

    response = ai.correct_meal_analysis(original_analysis, correction, profile_with_today)
    new_calories = _parse_calories(response)

    if meal_id:
        database.update_meal(meal_id, new_calories, {"ai_response": response, "calories": new_calories})

    await update.message.reply_text(f"Updated!\n\n{response}")
    logger.info("Corrected meal %s for user %d: %d kcal", meal_id, telegram_id, new_calories)


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
