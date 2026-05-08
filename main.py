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

from handlers.meal_log import log_handler, log_command_handler, photo_meal_handler
from handlers.meal_plan import meal_plan_handler
from handlers.plan import plan_handler
from handlers.report import report_handler
from handlers.restaurant import restaurant_handler
from handlers.settings import pause_handler, resume_handler
from handlers.start import start_conversation
from handlers.tests import tests_handler
from services.scheduler import setup_scheduler, shutdown_scheduler

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
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


async def smart_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    if _RESTAURANT_RE.search(text):
        await restaurant_handler(update, context)
    else:
        await log_handler(update, context)


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
    app.add_handler(CommandHandler("report", report_handler))
    app.add_handler(CommandHandler("plan", plan_handler))
    app.add_handler(CommandHandler("mealplan", meal_plan_handler))
    app.add_handler(CommandHandler("restaurant", restaurant_handler))
    app.add_handler(CommandHandler("tests", tests_handler))
    app.add_handler(CommandHandler("pause", pause_handler))
    app.add_handler(CommandHandler("resume", resume_handler))

    # Inline keyboard callbacks
    app.add_handler(CallbackQueryHandler(adjust_plan_callback, pattern="^adjust_plan_"))

    # Free-text fallback — routes to restaurant or general chat
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_router))

    app.run_polling()


if __name__ == "__main__":
    main()
