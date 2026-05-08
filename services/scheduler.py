import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from services import database

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _coaching_line(calories_in: int, target: int) -> str:
    if calories_in == 0:
        return "Nothing logged yet today — every meal logged is a step forward."
    deficit = target - calories_in
    if deficit >= 300:
        return f"Great work — you're {deficit} kcal under target. Keep it up!"
    if deficit >= 0:
        return f"Solid day — just {deficit} kcal left in your budget."
    return f"You're {abs(deficit)} kcal over today. A lighter dinner can help."


async def _daily_summary(bot) -> None:
    users = database.get_all_onboarded_users()
    logger.info("daily_summary: sending to %d users", len(users))
    for user in users:
        telegram_id = user["telegram_id"]
        try:
            target = user.get("calorie_target") or 0
            calories_in = database.get_today_calories(telegram_id)
            meal_count = database.get_today_meal_count(telegram_id)
            deficit = target - calories_in
            surplus_deficit = (
                f"Deficit: {deficit} kcal" if deficit >= 0 else f"Surplus: {abs(deficit)} kcal"
            )
            coaching = _coaching_line(calories_in, target)
            text = (
                f"\U0001f4ca *Daily Summary*\n\n"
                f"Calories: {calories_in} / {target} kcal\n"
                f"{surplus_deficit}\n"
                f"Meals logged: {meal_count}\n\n"
                f"_{coaching}_"
            )
            await bot.send_message(chat_id=telegram_id, text=text, parse_mode="Markdown")
        except Exception:
            logger.exception("daily_summary failed for telegram_id=%s", telegram_id)


async def _re_engagement(bot) -> None:
    users = database.get_users_inactive_48h()
    logger.info("re_engagement: sending to %d users", len(users))
    for user in users:
        telegram_id = user["telegram_id"]
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text="Haven't heard from you in a couple days. Want to log today's meals?",
            )
        except Exception:
            logger.exception("re_engagement failed for telegram_id=%s", telegram_id)


def setup_scheduler(bot) -> AsyncIOScheduler:
    global _scheduler
    _scheduler = AsyncIOScheduler()

    # 9 pm IST = 15:30 UTC
    _scheduler.add_job(
        _daily_summary,
        CronTrigger(hour=15, minute=30, timezone="UTC"),
        args=[bot],
        id="daily_summary",
    )

    # 7 pm IST = 13:30 UTC
    _scheduler.add_job(
        _re_engagement,
        CronTrigger(hour=13, minute=30, timezone="UTC"),
        args=[bot],
        id="re_engagement",
    )

    _scheduler.start()
    logger.info("Scheduler started — daily_summary@15:30 UTC, re_engagement@13:30 UTC")
    return _scheduler


def shutdown_scheduler() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
