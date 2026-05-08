import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from services import database

logger = logging.getLogger(__name__)

_WEIGHT_NUM_RE = re.compile(r"(\d+(?:\.\d+)?)")


async def weight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    if not user_profile:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    if context.args:
        raw = " ".join(context.args)
    else:
        raw = update.message.text or ""

    match = _WEIGHT_NUM_RE.search(raw)
    if not match:
        await update.message.reply_text("Usage: /weight <kg> (e.g. '/weight 75.5' or 'I weigh 75.5 today')")
        return

    new_weight = float(match.group(1))
    if not 20 <= new_weight <= 500:
        await update.message.reply_text("That doesn't look right. Enter your weight in kg (e.g. 75.5).")
        return

    database.log_weight(telegram_id=telegram_id, weight_kg=new_weight)
    database.update_user(telegram_id, {"weight_kg": new_weight})

    start_weight = user_profile.get("weight_kg", new_weight)
    target_weight = user_profile.get("target_weight_kg", new_weight)
    name = user_profile.get("name", "")

    lost = round(start_weight - new_weight, 1)
    to_go = round(new_weight - target_weight, 1)

    if lost > 0:
        progress_line = f"You're down {lost}kg from your starting weight."
    elif lost < 0:
        progress_line = f"You're up {abs(lost)}kg from your starting weight."
    else:
        progress_line = "Same as your starting weight — time to push."

    if to_go > 0:
        goal_line = f"{to_go}kg to your goal of {target_weight}kg. Keep going."
    elif to_go <= 0:
        goal_line = f"You've hit your goal weight of {target_weight}kg — incredible work, {name}!"
    else:
        goal_line = ""

    await update.message.reply_text(
        f"Logged: {new_weight}kg\n\n{progress_line} {goal_line}"
    )
    logger.info("Logged weight for user %d: %.1fkg", telegram_id, new_weight)
