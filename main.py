import logging
import os
import re

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from handlers.coach import coach_handler
from handlers.exercise import exercise_handler, handle_exercise_routine_state
from handlers.meal_log import log_handler, log_command_handler, photo_meal_handler, meal_correction_handler
from handlers.meal_plan import meal_plan_handler
from handlers.medication import medication_handler, handle_med_schedule_state
from handlers.plan import plan_handler
from handlers.report import report_handler
from handlers.restaurant import restaurant_handler
from handlers.settings import pause_handler, resume_handler
from handlers.start import start_conversation
from handlers.tests import tests_handler
from handlers.water import water_handler
from handlers.weight import weight_handler
from services.scheduler import setup_scheduler, shutdown_scheduler

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

_EXERCISE_RE = re.compile(
    r"(?i)\b(ran|run|walk|walked|workout|gym|yoga|cycl|swim|jog|exercise|hiit|cardio|played|training|trained|steps)\b"
)
_WATER_RE = re.compile(
    r"(?i)\b(water|glass|litre|liter|ml|hydrat|drank|drink)\b"
)
_WEIGHT_RE = re.compile(
    r"(?i)(i weigh|my weight|weighed|stepped on|scale|kg today)"
)
_MED_RE = re.compile(
    r"(?i)(took my|had my.*(pill|med|tablet)|took.*(mg|metformin|medicine))"
)
_RESTAURANT_RE = re.compile(
    r"(?i)(eating out|eating at|restaurant|cafe|going to\b)", re.IGNORECASE
)


async def photo_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    caption = update.message.caption or ""
    if re.search(r"(?i)report", caption):
        await report_handler(update, context)
    else:
        await photo_meal_handler(update, context)


async def _dispatch_pending_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = context.user_data.get("pending_state", {})
    state_type = state.get("type")
    if state_type == "med_schedule":
        await handle_med_schedule_state(update, context, state)
    elif state_type == "exercise_routine":
        await handle_exercise_routine_state(update, context, state)
    else:
        context.user_data.pop("pending_state", None)


async def smart_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""

    if context.user_data.get("pending_state"):
        await _dispatch_pending_state(update, context)
    elif context.user_data.get("last_meal_id"):
        await meal_correction_handler(update, context)
    elif _WEIGHT_RE.search(text):
        await weight_handler(update, context)
    elif _EXERCISE_RE.search(text):
        await exercise_handler(update, context)
    elif _WATER_RE.search(text):
        await water_handler(update, context)
    elif _MED_RE.search(text):
        await medication_handler(update, context)
    elif _RESTAURANT_RE.search(text):
        await restaurant_handler(update, context)
    else:
        await coach_handler(update, context)


async def adjust_plan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == "adjust_plan_yes":
        await query.edit_message_text("Run /mealplan to get an updated meal plan based on your latest report.")
    else:
        await query.edit_message_text("Got it — keeping your current plan.")


async def _post_init(app: Application) -> None:
    setup_scheduler(app.bot)


async def _post_shutdown(app: Application) -> None:
    shutdown_scheduler()


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    app = (
        Application.builder()
        .token(token)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )

    app.add_handler(start_conversation)

    # Document and photo handlers — order matters: specific before general
    app.add_handler(MessageHandler(filters.Document.PDF, report_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_router))

    # Command handlers
    app.add_handler(CommandHandler("log", log_command_handler))
    app.add_handler(CommandHandler("exercise", exercise_handler))
    app.add_handler(CommandHandler("water", water_handler))
    app.add_handler(CommandHandler("weight", weight_handler))
    app.add_handler(CommandHandler("medication", medication_handler))
    app.add_handler(CommandHandler("report", report_handler))
    app.add_handler(CommandHandler("plan", plan_handler))
    app.add_handler(CommandHandler("mealplan", meal_plan_handler))
    app.add_handler(CommandHandler("restaurant", restaurant_handler))
    app.add_handler(CommandHandler("tests", tests_handler))
    app.add_handler(CommandHandler("pause", pause_handler))
    app.add_handler(CommandHandler("resume", resume_handler))

    # Inline keyboard callbacks
    app.add_handler(CallbackQueryHandler(adjust_plan_callback, pattern="^adjust_plan_"))

    # Free-text fallback — smart router handles intent detection
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_router))

    app.run_polling()


if __name__ == "__main__":
    main()
