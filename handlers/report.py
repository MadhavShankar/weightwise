import logging

import fitz  # PyMuPDF
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from services import ai, database

logger = logging.getLogger(__name__)


def _pdf_first_page_bytes(pdf_bytes: bytes) -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    return pix.tobytes("png")


async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user_profile = database.get_user(telegram_id)
    if not user_profile:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    image_bytes: bytes | None = None

    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        image_bytes = bytes(await photo_file.download_as_bytearray())
    elif update.message.document and update.message.document.mime_type == "application/pdf":
        doc_file = await update.message.document.get_file()
        pdf_bytes = bytes(await doc_file.download_as_bytearray())
        image_bytes = _pdf_first_page_bytes(pdf_bytes)
    else:
        await update.message.reply_text(
            "Send me a photo or PDF of your lab report and I'll analyse it for you."
        )
        return

    await update.message.reply_text("Analysing your lab report...")

    summary = ai.analyze_lab_report(image_bytes)
    database.save_report_summary(telegram_id, summary)

    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("Yes", callback_data="adjust_plan_yes"),
            InlineKeyboardButton("No", callback_data="adjust_plan_no"),
        ]]
    )
    await update.message.reply_text(
        f"{summary}\n\nWant me to adjust your meal plan?",
        reply_markup=keyboard,
    )
    logger.info("Saved lab report summary for user %d", telegram_id)
