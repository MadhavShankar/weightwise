import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from services import ai, database

logger = logging.getLogger(__name__)

_CALORIES_RE = re.compile(r"Calories:\s*(\d+)")
_NO_CHANGE_RE = re.compile(
    r"\b(no changes?|same as before|nothing new|no updates?|nothing to log|all good|nothing different|no change today)\b",
    re.IGNORECASE,
)
_FOOD_NAME_RE = re.compile(r"FoodName:\s*(.+)")
_FOODS_RE = re.compile(r"Foods:\s*(.+)")
_QUANTITY_TYPE_RE = re.compile(r"QuantityType:\s*(whole|slice|bowl|serving|unit)", re.IGNORECASE)


def _parse_calories(response: str) -> int:
    match = _CALORIES_RE.search(response)
    if match:
        return int(match.group(1))
    logger.warning("Could not parse calories from AI response")
    return 0


def _parse_display_name(response: str) -> tuple[str, bool]:
    """Returns (display_name, is_multiple). is_multiple=True when more than one food item."""
    foods_match = _FOODS_RE.search(response)
    if foods_match:
        items = [f.strip() for f in foods_match.group(1).split(",") if f.strip()]
        if len(items) == 2:
            return f"{items[0]} and {items[1]}", True
        if len(items) >= 3:
            return f"{items[0]}, {items[1]} and {items[2]}", True

    name_match = _FOOD_NAME_RE.search(response)
    return (name_match.group(1).strip() if name_match else "meal"), False


def _parse_quantity_type(response: str) -> str:
    match = _QUANTITY_TYPE_RE.search(response)
    return match.group(1).strip().lower() if match else "serving"


def _quantity_correction_prompt(food_name: str, quantity_type: str, is_multiple: bool = False) -> str:
    if is_multiple:
        return "Got something wrong? Reply to correct (e.g., 'actually large fries, not medium')."
    food = food_name or "that"
    if quantity_type == "whole":
        return f"Wrong count? Reply with how many {food} you had."
    if quantity_type == "slice":
        return f"Wrong slices? Reply with how many slices of {food} you had."
    if quantity_type == "bowl":
        return f"Wrong? Reply with how many bowls of {food}."
    if quantity_type == "unit":
        return f"Wrong count? Reply with how many {food} you had."
    return "Off on the servings? Reply to correct."


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

    food_name, is_multiple = _parse_display_name(response)
    quantity_type = _parse_quantity_type(response)
    total = today_calories + calories
    correction_hint = _quantity_correction_prompt(food_name, quantity_type, is_multiple)

    await update.message.reply_text(
        f"Updated your {food_name}. As per analysis, it seems the calorie count is {calories} kcal. "
        f"Your total calorie consumption is {total} kcal.\n\n{correction_hint}"
    )
    logger.info("Logged meal for user %d: %d kcal", telegram_id, calories)


async def meal_correction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    if not user_profile:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    correction = update.message.text or ""

    if _NO_CHANGE_RE.search(correction):
        context.user_data.pop("last_meal_id", None)
        context.user_data.pop("last_meal_analysis", None)
        context.user_data.pop("last_meal_today_calories", None)
        await update.message.reply_text("Noted.")
        return

    meal_id = context.user_data.pop("last_meal_id", None)
    original_analysis = context.user_data.pop("last_meal_analysis", "")
    context.user_data.pop("last_meal_today_calories", 0)

    today_calories = database.get_today_calories(telegram_id)
    profile_with_today = {**user_profile, "today_calories": today_calories}

    response = ai.correct_meal_analysis(original_analysis, correction, profile_with_today)
    new_calories = _parse_calories(response)

    if meal_id:
        database.update_meal(meal_id, new_calories, {"ai_response": response, "calories": new_calories})

    food_name, _ = _parse_display_name(response)
    total = database.get_today_calories(telegram_id)

    await update.message.reply_text(
        f"Updated your {food_name}. As per analysis, it seems the calorie count is {new_calories} kcal. "
        f"Your total calorie consumption is {total} kcal."
    )
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
    meal_id = database.log_meal(
        telegram_id=telegram_id,
        description=description,
        calories=calories,
        meal_data={"ai_response": response, "calories": calories},
    )

    context.user_data["last_meal_id"] = meal_id
    context.user_data["last_meal_analysis"] = response
    context.user_data["last_meal_today_calories"] = today_calories

    food_name, is_multiple = _parse_display_name(response)
    quantity_type = _parse_quantity_type(response)
    total = today_calories + calories
    correction_hint = _quantity_correction_prompt(food_name, quantity_type, is_multiple)

    await update.message.reply_text(
        f"Updated your {food_name}. As per analysis, it seems the calorie count is {calories} kcal. "
        f"Your total calorie consumption is {total} kcal.\n\n{correction_hint}"
    )
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
    meal_id = database.log_meal(
        telegram_id=telegram_id,
        description=description,
        calories=calories,
        meal_data={"ai_response": response, "calories": calories},
    )

    context.user_data["last_meal_id"] = meal_id
    context.user_data["last_meal_analysis"] = response
    context.user_data["last_meal_today_calories"] = today_calories

    food_name, is_multiple = _parse_display_name(response)
    quantity_type = _parse_quantity_type(response)
    total = today_calories + calories
    correction_hint = _quantity_correction_prompt(food_name, quantity_type, is_multiple)

    await update.message.reply_text(
        f"Updated your {food_name}. As per analysis, it seems the calorie count is {calories} kcal. "
        f"Your total calorie consumption is {total} kcal.\n\n{correction_hint}"
    )
    logger.info("Logged text meal for user %d: %d kcal", telegram_id, calories)
