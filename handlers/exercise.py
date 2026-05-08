import logging
import re
from datetime import datetime

import pytz

from telegram import Update
from telegram.ext import ContextTypes

from services import ai, database

logger = logging.getLogger(__name__)

_IST = pytz.timezone("Asia/Kolkata")

_TYPE_RE = re.compile(r"Type:\s*(.+)", re.IGNORECASE)
_DURATION_RE = re.compile(r"Duration:\s*(\d+)", re.IGNORECASE)
_BURNED_RE = re.compile(r"Burned:\s*(\d+)", re.IGNORECASE)

_DAY_NAMES = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

_FREQ_RE = re.compile(r"(\d+)\s*(?:times?|x)\s*(?:a|per)?\s*week", re.IGNORECASE)


def _parse_frequency(text: str) -> int:
    m = _FREQ_RE.search(text)
    if m:
        return int(m.group(1))
    if re.search(r"\bdaily\b|\bevery\s+day\b", text, re.I):
        return 7
    return 3


def _parse_days(text: str) -> list[int]:
    low = text.lower()
    if "weekday" in low:
        return [0, 1, 2, 3, 4]
    if "weekend" in low:
        return [5, 6]
    return sorted({v for k, v in _DAY_NAMES.items() if k in low})


def _routine_adherence(routine: dict, name: str, exercise_type: str) -> str:
    preferred_days_str = routine.get("preferred_days", "")
    freq = routine.get("frequency_per_week", 0)
    routine_type = routine.get("exercise_type", "workout")

    day_indices = _parse_days(preferred_days_str)
    today_idx = datetime.now(_IST).weekday()

    if not day_indices:
        return (
            f"On track with your {routine_type} routine, {name}. "
            f"That's {freq}x/week — keep the discipline."
        )

    if today_idx in day_indices:
        return (
            f"Right on schedule, {name} — today is one of your {routine_type} days. "
            f"Great that you got it done."
        )

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    scheduled = ", ".join(day_names[d] for d in day_indices)
    return (
        f"Bonus session, {name} — today isn't one of your scheduled {routine_type} days "
        f"({scheduled}). Extra work like this is what separates good from great."
    )


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
        await update.message.reply_text(
            "Usage: /exercise <what you did> or just describe it (e.g. 'went for a 30 min run')"
        )
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

    routine = database.get_exercise_routine(telegram_id)

    if routine:
        adherence = _routine_adherence(routine, user_profile.get("name", ""), exercise_type)
        await update.message.reply_text(f"{response}\n\n{adherence}")
    else:
        context.user_data["pending_state"] = {
            "type": "exercise_routine",
            "exercise_type": exercise_type,
            "step": "ask_regular",
        }
        await update.message.reply_text(
            f"{response}\n\nIs {exercise_type} part of your regular routine? (yes / no)"
        )

    logger.info(
        "Logged exercise for user %d: %s, %d min, %d kcal burned",
        telegram_id, exercise_type, duration, burned,
    )


async def handle_exercise_routine_state(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: dict
) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    name = user_profile.get("name", "") if user_profile else ""

    text = (update.message.text or "").strip()
    low = text.lower()
    step = state.get("step")
    exercise_type = state.get("exercise_type", "workout")

    if step == "ask_regular":
        if low in ("yes", "y", "yeah", "yep", "sure", "yup", "yes please"):
            context.user_data["pending_state"] = {**state, "step": "ask_frequency"}
            await update.message.reply_text(
                f"How many times a week do you plan to do {exercise_type}? "
                f"(e.g. '3 times a week', 'daily')"
            )
        else:
            context.user_data.pop("pending_state", None)
            await update.message.reply_text(
                f"No problem — logged as a one-off session. Let me know when you want to set up a routine."
            )

    elif step == "ask_frequency":
        freq = _parse_frequency(text)
        context.user_data["pending_state"] = {
            **state,
            "step": "ask_days",
            "frequency": freq,
        }
        await update.message.reply_text(
            f"Which days do you plan to train? "
            f"(e.g. 'Mon, Wed, Fri' or 'weekdays' or 'every day')"
        )

    elif step == "ask_days":
        freq = state.get("frequency", 3)
        database.save_exercise_routine(
            telegram_id=telegram_id,
            exercise_type=exercise_type,
            frequency_per_week=freq,
            preferred_days=text,
        )
        context.user_data.pop("pending_state", None)
        await update.message.reply_text(
            f"Routine saved — {exercise_type} {freq}x/week on {text}. "
            f"I'll keep you accountable, {name}. Miss a day and I'll notice."
        )
