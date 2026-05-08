import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from services import ai, database

logger = logging.getLogger(__name__)

_TYPE_RE = re.compile(r"Type:\s*(.+)", re.IGNORECASE)
_DURATION_RE = re.compile(r"Duration:\s*(\d+)", re.IGNORECASE)
_BURNED_RE = re.compile(r"Burned:\s*(\d+)", re.IGNORECASE)


def _parse_exercise(response: str) -> tuple[str, int, int]:
    exercise_type = (_TYPE_RE.search(response) or type("", (), {"group": lambda s, n: "general workout"})()).group(1)
    duration = int(_DURATION_RE.search(response).group(1)) if _DURATION_RE.search(response) else 30
    burned = int(_BURNED_RE.search(response).group(1)) if _BURNED_RE.search(response) else 0
    return exercise_type, duration, burned


async def exercise_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        await update.message.reply_text("Usage: /exercise <what you did> or just describe it (e.g. 'went for a 30 min run')")
        return

    response = ai.analyze_exercise(description, user_profile)

    type_match = _TYPE_RE.search(response)
    duration_match = _DURATION_RE.search(response)
    burned_match = _BURNED_RE.search(response)

    exercise_type = type_match.group(1).strip() if type_match else "general workout"
    duration = int(duration_match.group(1)) if duration_match else 30
    burned = int(burned_match.group(1)) if burned_match else 0

    database.log_exercise(
        telegram_id=telegram_id,
        description=description,
        exercise_type=exercise_type,
        duration_min=duration,
        calories_burned=burned,
    )

    await update.message.reply_text(response)
    logger.info("Logged exercise for user %d: %s, %d min, %d kcal burned", telegram_id, exercise_type, duration, burned)
