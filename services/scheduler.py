import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from services import ai, database

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _get_yesterday_stats(telegram_id: int) -> dict:
    client = database._get_client()
    yesterday_start = (datetime.now(timezone.utc) - timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    yesterday_end = yesterday_start + timedelta(days=1)

    meals = (
        client.table("meal_logs")
        .select("calories")
        .eq("telegram_id", telegram_id)
        .gte("logged_at", yesterday_start.isoformat())
        .lt("logged_at", yesterday_end.isoformat())
        .execute()
    )
    calories = sum(r["calories"] for r in meals.data)

    water = (
        client.table("water_logs")
        .select("amount_ml")
        .eq("telegram_id", telegram_id)
        .gte("logged_at", yesterday_start.isoformat())
        .lt("logged_at", yesterday_end.isoformat())
        .execute()
    )
    water_ml = sum(r["amount_ml"] for r in water.data)

    exercise = (
        client.table("exercise_logs")
        .select("calories_burned")
        .eq("telegram_id", telegram_id)
        .gte("logged_at", yesterday_start.isoformat())
        .lt("logged_at", yesterday_end.isoformat())
        .execute()
    )
    exercise_calories = sum(r["calories_burned"] for r in exercise.data)

    return {"calories": calories, "water_ml": water_ml, "exercise_calories": exercise_calories}


async def _morning_motivation(bot) -> None:
    users = database.get_all_onboarded_users()
    logger.info("morning_motivation: sending to %d users", len(users))
    for user in users:
        telegram_id = user["telegram_id"]
        try:
            user_profile = database.get_user(telegram_id)
            if not user_profile:
                continue
            yesterday_stats = _get_yesterday_stats(telegram_id)
            message = ai.generate_morning_motivation(user_profile, yesterday_stats)
            await bot.send_message(chat_id=telegram_id, text=message)
        except Exception:
            logger.exception("morning_motivation failed for telegram_id=%s", telegram_id)


async def _midday_water_nudge(bot) -> None:
    users = database.get_all_onboarded_users()
    logger.info("midday_water_nudge: checking %d users", len(users))
    for user in users:
        telegram_id = user["telegram_id"]
        try:
            water_ml = database.get_today_water_ml(telegram_id)
            if water_ml < 500:
                name = user.get("name", "")
                await bot.send_message(
                    chat_id=telegram_id,
                    text=f"Hey {name}, you've only had {water_ml}ml of water so far today. Grab a glass now — hydration keeps hunger in check.",
                )
        except Exception:
            logger.exception("midday_water_nudge failed for telegram_id=%s", telegram_id)


async def _evening_summary(bot) -> None:
    users = database.get_all_onboarded_users()
    logger.info("evening_summary: sending to %d users", len(users))
    for user in users:
        telegram_id = user["telegram_id"]
        try:
            user_profile = database.get_user(telegram_id)
            if not user_profile:
                continue

            calories_in = database.get_today_calories(telegram_id)
            exercise_calories = database.get_today_exercise_calories(telegram_id)
            water_ml = database.get_today_water_ml(telegram_id)
            meal_count = database.get_today_meal_count(telegram_id)

            calorie_target = user_profile.get("calorie_target") or 0
            net_calories = calories_in - exercise_calories
            hit_target = net_calories <= calorie_target

            streak_result = database.update_streak(telegram_id, hit_target)

            daily_stats = {
                "calories_in": calories_in,
                "exercise_calories": exercise_calories,
                "net_calories": net_calories,
                "water_ml": water_ml,
                "meal_count": meal_count,
                "current_streak": streak_result["current"],
                "milestone": streak_result["milestone"],
            }

            full_profile = database.get_user(telegram_id)
            message = ai.generate_evening_summary(full_profile, daily_stats)
            await bot.send_message(chat_id=telegram_id, text=message)
        except Exception:
            logger.exception("evening_summary failed for telegram_id=%s", telegram_id)


async def _weekly_pattern_analysis(bot) -> None:
    users = database.get_all_onboarded_users()
    logger.info("weekly_pattern_analysis: analyzing %d users", len(users))
    for user in users:
        telegram_id = user["telegram_id"]
        try:
            user_profile = database.get_user(telegram_id)
            if not user_profile:
                continue
            meal_history = database.get_weekly_meals(telegram_id)
            if not meal_history:
                continue
            summary = ai.analyze_eating_patterns(meal_history, user_profile)
            database.save_pattern_summary(telegram_id, summary)
            logger.info("Pattern summary updated for user %d", telegram_id)
        except Exception:
            logger.exception("weekly_pattern_analysis failed for telegram_id=%s", telegram_id)


async def _re_engagement(bot) -> None:
    users = database.get_users_inactive_48h()
    logger.info("re_engagement: sending to %d users", len(users))
    for user in users:
        telegram_id = user["telegram_id"]
        try:
            name = user.get("name", "")
            await bot.send_message(
                chat_id=telegram_id,
                text=f"Hey {name}, I haven't seen you log anything in a couple of days. No pressure — just checking in. Even logging one meal today gets you back on track.",
            )
        except Exception:
            logger.exception("re_engagement failed for telegram_id=%s", telegram_id)


def setup_scheduler(bot) -> AsyncIOScheduler:
    global _scheduler
    _scheduler = AsyncIOScheduler()

    # 8:30am IST = 03:00 UTC
    _scheduler.add_job(
        _morning_motivation,
        CronTrigger(hour=3, minute=0, timezone="UTC"),
        args=[bot],
        id="morning_motivation",
    )

    # 1pm IST = 07:30 UTC
    _scheduler.add_job(
        _midday_water_nudge,
        CronTrigger(hour=7, minute=30, timezone="UTC"),
        args=[bot],
        id="midday_water_nudge",
    )

    # 9pm IST = 15:30 UTC
    _scheduler.add_job(
        _evening_summary,
        CronTrigger(hour=15, minute=30, timezone="UTC"),
        args=[bot],
        id="evening_summary",
    )

    # Sunday 8pm IST = Sunday 14:30 UTC
    _scheduler.add_job(
        _weekly_pattern_analysis,
        CronTrigger(day_of_week="sun", hour=14, minute=30, timezone="UTC"),
        args=[bot],
        id="weekly_pattern_analysis",
    )

    # 7pm IST = 13:30 UTC
    _scheduler.add_job(
        _re_engagement,
        CronTrigger(hour=13, minute=30, timezone="UTC"),
        args=[bot],
        id="re_engagement",
    )

    _scheduler.start()
    logger.info(
        "Scheduler started — morning@03:00, water_nudge@07:30, evening@15:30, patterns@Sun14:30, re_engagement@13:30 UTC"
    )
    return _scheduler


def shutdown_scheduler() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
