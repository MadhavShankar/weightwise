import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from services import ai, database

logger = logging.getLogger(__name__)

_INTENT_RE = re.compile(r"^INTENT:\s*(meal|chat|no_change)", re.IGNORECASE | re.MULTILINE)
_CALORIES_RE = re.compile(r"Calories:\s*(\d+)")
_FOOD_NAME_RE = re.compile(r"FoodName:\s*(.+)")
_FOODS_RE = re.compile(r"Foods:\s*(.+)")
_QUANTITY_TYPE_RE = re.compile(r"QuantityType:\s*(whole|slice|bowl|serving|unit)", re.IGNORECASE)


def _parse_display_name(response: str) -> tuple[str, bool]:
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


def _get_proactive_nudge(telegram_id: int, user_profile: dict, context) -> str | None:
    if context.user_data.get("profile_nudge_sent"):
        return None

    days_since_weight = database.get_days_since_weight_log(telegram_id)
    name = user_profile.get("name", "")

    if days_since_weight is None:
        context.user_data["profile_nudge_sent"] = True
        return f"By the way — I don't have a weight log for you yet. Use /weight to log it so I can track your progress."

    if days_since_weight >= 7:
        context.user_data["profile_nudge_sent"] = True
        return f"Quick note, {name}: your last weight log was {days_since_weight} days ago. Use /weight to update it — weekly weigh-ins make a real difference to tracking."

    return None


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

        food_name, is_multiple = _parse_display_name(response)
        quantity_type = _parse_quantity_type(response)
        total = today_calories + calories
        correction_hint = _quantity_correction_prompt(food_name, quantity_type, is_multiple)

        await update.message.reply_text(
            f"Updated your {food_name}. As per analysis, it seems the calorie count is {calories} kcal. "
            f"Your total calorie consumption is {total} kcal.\n\n{correction_hint}"
        )
        logger.info("Coach routed meal for user %d: %d kcal", telegram_id, calories)
    elif intent == "no_change":
        await update.message.reply_text("Noted.")
        logger.info("Coach no_change for user %d", telegram_id)
    else:
        clean_response = _INTENT_RE.sub("", response).strip()
        await update.message.reply_text(clean_response)
        logger.info("Coach chat for user %d", telegram_id)

    nudge = _get_proactive_nudge(telegram_id, user_profile, context)
    if nudge:
        await update.message.reply_text(nudge)
