import logging

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from services import calculator, database

logger = logging.getLogger(__name__)

ASK_NAME, ASK_AGE, ASK_GENDER, ASK_HEIGHT, ASK_WEIGHT, ASK_TARGET_WEIGHT, ASK_ACTIVITY, ASK_DIET, ASK_MEDICAL = range(9)

_GENDER_KB = ReplyKeyboardMarkup([["Male", "Female"]], one_time_keyboard=True, resize_keyboard=True)
_ACTIVITY_KB = ReplyKeyboardMarkup([["Sedentary", "Light", "Moderate", "Active"]], one_time_keyboard=True, resize_keyboard=True)


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    user = database.get_user(telegram_id)

    if user:
        calories_today = database.get_today_calories(telegram_id)
        target = user.get("calorie_target") or 0
        remaining = target - calories_today
        await update.message.reply_text(
            f"Welcome back, {user['name']}!\n\n"
            f"Today: {calories_today} / {target} kcal\n"
            f"Remaining: {remaining} kcal",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Welcome to WeightWise! Let's set up your profile.\n\nWhat's your name?"
    )
    return ASK_NAME


async def _ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("How old are you?")
    return ASK_AGE


async def _ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age = int(update.message.text.strip())
        if not 10 <= age <= 120:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a valid age (e.g. 28).")
        return ASK_AGE

    context.user_data["age"] = age
    await update.message.reply_text("What's your gender?", reply_markup=_GENDER_KB)
    return ASK_GENDER


async def _ask_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if text not in ("male", "female"):
        await update.message.reply_text("Please choose Male or Female.", reply_markup=_GENDER_KB)
        return ASK_GENDER

    context.user_data["gender"] = text
    await update.message.reply_text("What's your height in cm? (e.g. 175)", reply_markup=ReplyKeyboardRemove())
    return ASK_HEIGHT


async def _ask_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        height = float(update.message.text.strip())
        if not 50 <= height <= 300:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a valid height in cm (e.g. 175).")
        return ASK_HEIGHT

    context.user_data["height_cm"] = height
    await update.message.reply_text("What's your current weight in kg? (e.g. 80.5)")
    return ASK_WEIGHT


async def _ask_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        weight = float(update.message.text.strip())
        if not 20 <= weight <= 500:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a valid weight in kg (e.g. 80.5).")
        return ASK_WEIGHT

    context.user_data["weight_kg"] = weight
    await update.message.reply_text("What's your target weight in kg? (e.g. 70)")
    return ASK_TARGET_WEIGHT


async def _ask_target_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        target = float(update.message.text.strip())
        if not 20 <= target <= 500:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a valid target weight in kg.")
        return ASK_TARGET_WEIGHT

    context.user_data["target_weight_kg"] = target
    await update.message.reply_text("What's your activity level?", reply_markup=_ACTIVITY_KB)
    return ASK_ACTIVITY


async def _ask_activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if text not in ("sedentary", "light", "moderate", "active"):
        await update.message.reply_text(
            "Please choose one: Sedentary, Light, Moderate, Active.",
            reply_markup=_ACTIVITY_KB,
        )
        return ASK_ACTIVITY

    context.user_data["activity_level"] = text
    await update.message.reply_text(
        "Any dietary preference? (e.g. vegetarian, vegan, none)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_DIET


async def _ask_diet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["diet_preference"] = update.message.text.strip()
    await update.message.reply_text(
        "Any medical conditions we should know about? (e.g. diabetes, none)"
    )
    return ASK_MEDICAL


async def _ask_medical(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    data = context.user_data
    data["medical_conditions"] = update.message.text.strip()

    bmr = calculator.calculate_bmr(data["weight_kg"], data["height_cm"], data["age"], data["gender"])
    tdee = calculator.calculate_tdee(bmr, data["activity_level"])
    calorie_target = calculator.calculate_calorie_target(tdee)
    macros = calculator.calculate_macros(calorie_target, data["weight_kg"])

    database.create_user(telegram_id, data["name"])
    database.update_user(telegram_id, {
        "age": data["age"],
        "gender": data["gender"],
        "height_cm": data["height_cm"],
        "weight_kg": data["weight_kg"],
        "target_weight_kg": data["target_weight_kg"],
        "activity_level": data["activity_level"],
        "diet_preference": data["diet_preference"],
        "medical_conditions": data["medical_conditions"],
        "calorie_target": calorie_target,
        "onboarding_complete": True,
    })

    logger.info("New user created: telegram_id=%s calorie_target=%s", telegram_id, calorie_target)

    await update.message.reply_text(
        f"All set, {data['name']}! Here's your daily plan:\n\n"
        f"Calorie target: {calorie_target} kcal\n"
        f"Protein: {macros['protein_g']}g\n"
        f"Carbs: {macros['carbs_g']}g\n"
        f"Fat: {macros['fat_g']}g\n\n"
        "Just send me what you eat and I'll track it!",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Setup cancelled. Send /start to begin again.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END


start_conversation = ConversationHandler(
    entry_points=[CommandHandler("start", _start)],
    states={
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_name)],
        ASK_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_age)],
        ASK_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_gender)],
        ASK_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_height)],
        ASK_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_weight)],
        ASK_TARGET_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_target_weight)],
        ASK_ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_activity)],
        ASK_DIET: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_diet)],
        ASK_MEDICAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_medical)],
    },
    fallbacks=[CommandHandler("cancel", _cancel)],
)
