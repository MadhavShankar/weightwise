import logging
import re
from datetime import datetime

import pytz

from telegram import Update
from telegram.ext import ContextTypes

from services import ai, database

logger = logging.getLogger(__name__)

_IST = pytz.timezone("Asia/Kolkata")

_NAMED_TIMES = {
    "morning": 8,
    "afternoon": 13,
    "noon": 12,
    "evening": 18,
    "night": 21,
    "bedtime": 22,
    "midnight": 0,
    "lunch": 13,
    "dinner": 19,
    "breakfast": 8,
}


def _parse_hours(schedule_times: str) -> list[int]:
    hours = []
    low = schedule_times.lower()

    for word, h in _NAMED_TIMES.items():
        if word in low and h not in hours:
            hours.append(h)

    for m in re.finditer(r'\b(\d{1,2})(?::00)?\s*(am|pm)?\b', low):
        h = int(m.group(1))
        suffix = m.group(2)
        if suffix == "pm" and h < 12:
            h += 12
        elif suffix == "am" and h == 12:
            h = 0
        if h not in hours:
            hours.append(h)

    return sorted(hours)


def _fmt_hour(h: int) -> str:
    if h == 0:
        return "12am"
    if h < 12:
        return f"{h}am"
    if h == 12:
        return "12pm"
    return f"{h - 12}pm"


def _adherence_message(schedule: dict, name: str) -> str:
    med_name = schedule.get("medication_name", "medication")
    schedule_times = schedule.get("schedule_times", "")

    hours = _parse_hours(schedule_times)
    if not hours:
        return f"Noted — {med_name} logged."

    now_ist = datetime.now(_IST)
    current_hour = now_ist.hour

    diffs = sorted((abs(h - current_hour), h) for h in hours)
    closest_diff, closest_hour = diffs[0]

    if closest_diff <= 1:
        return f"Good — {med_name} right on time."

    if closest_diff <= 3:
        return f"{name}, you're late on your {med_name}. Take it now."

    future = [h for h in hours if h > current_hour]
    if future:
        return f"Noted — {med_name} logged. Next dose at {_fmt_hour(min(future))}."

    return f"All {med_name} doses done today. Good."


async def medication_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    if not user_profile:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    text = update.message.text or ""
    name = user_profile.get("name", "")

    med_name = ai.extract_medication_name(text)
    database.log_medication(telegram_id=telegram_id, medication_name=med_name)

    schedule = database.get_medication_schedule(telegram_id, med_name)

    if schedule:
        await update.message.reply_text(_adherence_message(schedule, name))
    else:
        await update.message.reply_text(f"Noted — {med_name} logged.")

    logger.info("Logged medication for user %d: %s", telegram_id, med_name)


async def handle_med_schedule_state(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: dict
) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    name = user_profile.get("name", "") if user_profile else ""

    text = (update.message.text or "").strip()
    low = text.lower()
    step = state.get("step")
    med_name = state.get("name", "medication")

    if step == "ask_regular":
        if low in ("yes", "y", "yeah", "yep", "sure", "yup", "yes please"):
            context.user_data["pending_state"] = {**state, "step": "ask_frequency"}
            await update.message.reply_text(
                f"How often do you take {med_name}? "
                f"(e.g. once daily, twice daily, with meals, as needed)"
            )
        else:
            context.user_data.pop("pending_state", None)
            await update.message.reply_text(
                f"Got it — logged {med_name} as a one-off."
            )

    elif step == "ask_frequency":
        context.user_data["pending_state"] = {
            **state,
            "step": "ask_times",
            "frequency": text,
        }
        await update.message.reply_text(
            f"At what time(s) do you usually take it? "
            f"(e.g. '8am and 8pm', 'morning and night', 'with each meal')"
        )

    elif step == "ask_times":
        frequency = state.get("frequency", "")
        database.save_medication_schedule(
            telegram_id=telegram_id,
            medication_name=med_name,
            frequency=frequency,
            schedule_times=text,
        )
        context.user_data.pop("pending_state", None)
        await update.message.reply_text(
            f"Schedule saved for {med_name}: {frequency} at {text}. "
            f"I'll flag it if you're running late, {name}."
        )
