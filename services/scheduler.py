import logging
import re
from datetime import datetime, timezone, timedelta

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from services import ai, database

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_IST = pytz.timezone("Asia/Kolkata")

# ── Shared parsing helpers ────────────────────────────────────────────────────

_NAMED_HOURS = {
    "morning": 8, "breakfast": 8,
    "noon": 12, "lunch": 13, "afternoon": 13,
    "evening": 18, "dinner": 19,
    "night": 21, "bedtime": 22,
}

_DAY_MAP = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}


def _parse_schedule_hours(schedule_times: str) -> list[int]:
    hours = []
    low = schedule_times.lower()
    for word, h in _NAMED_HOURS.items():
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


def _parse_routine_days(preferred_days: str) -> list[int]:
    low = preferred_days.lower()
    if "every day" in low or "daily" in low:
        return list(range(7))
    if "weekday" in low:
        return [0, 1, 2, 3, 4]
    if "weekend" in low:
        return [5, 6]
    return sorted({v for k, v in _DAY_MAP.items() if k in low})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_water_goal_ml(user_profile: dict) -> int:
    """Daily water goal in ml from weight + activity. Falls back to 2500ml."""
    stored = user_profile.get("water_goal_ml")
    if stored:
        return int(stored)
    weight = user_profile.get("weight_kg") or 0
    if not weight:
        return 2500
    activity = (user_profile.get("activity_level") or "").lower()
    if any(w in activity for w in ("very active", "highly active", "athlete")):
        ml_per_kg = 40
    elif any(w in activity for w in ("active", "moderate")):
        ml_per_kg = 35
    else:
        ml_per_kg = 30
    return int(weight * ml_per_kg)


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


# ── Scheduled jobs ────────────────────────────────────────────────────────────

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


async def _water_nudge(bot) -> None:
    """Fires 4× daily. Skips users who have already met their water goal."""
    users = database.get_all_onboarded_users()
    logger.info("water_nudge: checking %d users", len(users))
    for user in users:
        telegram_id = user["telegram_id"]
        try:
            user_profile = database.get_user(telegram_id)
            if not user_profile:
                continue
            water_ml = database.get_today_water_ml(telegram_id)
            water_goal = _get_water_goal_ml(user_profile)
            if water_ml >= water_goal:
                continue
            name = user_profile.get("name", "")
            remaining = water_goal - water_ml
            await bot.send_message(
                chat_id=telegram_id,
                text=(
                    f"{name}, water check: {water_ml}ml so far today, goal is {water_goal}ml. "
                    f"{remaining}ml still to go — grab a glass now."
                ),
            )
        except Exception:
            logger.exception("water_nudge failed for telegram_id=%s", telegram_id)


async def _medication_routine_nudge(bot) -> None:
    """Fire for any user whose scheduled medication dose is due now and not yet logged."""
    paused = {u["telegram_id"] for u in database.get_all_onboarded_users() if u.get("notifications_paused")}
    all_schedules = database.get_all_medication_schedules()

    now_ist = datetime.now(_IST)
    current_hour = now_ist.hour

    logger.info("medication_routine_nudge: checking %d schedules at IST hour %d", len(all_schedules), current_hour)

    for sched in all_schedules:
        telegram_id = sched["telegram_id"]
        if telegram_id in paused:
            continue

        med_name = sched.get("medication_name", "medication")
        schedule_times = sched.get("schedule_times", "")

        hours = _parse_schedule_hours(schedule_times)
        if not hours:
            continue

        # Only nudge if a scheduled dose falls within ±1 hour of now
        if not any(abs(h - current_hour) <= 1 for h in hours):
            continue

        # Skip if already logged in the past 2 hours
        if database.get_recent_medication_log(telegram_id, med_name, hours=2):
            continue

        try:
            user = database.get_user(telegram_id)
            if not user:
                continue
            name = user.get("name", "")
            frequency = sched.get("frequency", "")
            await bot.send_message(
                chat_id=telegram_id,
                text=(
                    f"Hey {name} — time for your {med_name}"
                    + (f" ({frequency})" if frequency else "")
                    + ". Don't skip it."
                ),
            )
            logger.info("Medication nudge sent to %d for %s", telegram_id, med_name)
        except Exception:
            logger.exception("medication_routine_nudge failed for telegram_id=%s", telegram_id)


async def _exercise_routine_nudge(bot) -> None:
    """Fire for any user who has a scheduled workout today but hasn't logged it yet."""
    paused = {u["telegram_id"] for u in database.get_all_onboarded_users() if u.get("notifications_paused")}
    all_routines = database.get_all_exercise_routines()

    today_idx = datetime.now(_IST).weekday()

    logger.info("exercise_routine_nudge: checking %d routines on weekday %d", len(all_routines), today_idx)

    for routine in all_routines:
        telegram_id = routine["telegram_id"]
        if telegram_id in paused:
            continue

        preferred_days = routine.get("preferred_days", "")
        exercise_type = routine.get("exercise_type", "workout")
        freq = routine.get("frequency_per_week", 0)

        day_indices = _parse_routine_days(preferred_days)
        # If days were stored but today is not one of them, skip
        if day_indices and today_idx not in day_indices:
            continue

        # Skip if exercise already logged today
        if database.has_exercise_today(telegram_id):
            continue

        try:
            user = database.get_user(telegram_id)
            if not user:
                continue
            name = user.get("name", "")
            days_label = preferred_days if preferred_days else f"{freq}x/week"
            await bot.send_message(
                chat_id=telegram_id,
                text=(
                    f"{name}, today is one of your scheduled {exercise_type} days "
                    f"({days_label}). You haven't logged it yet — still time to get it done."
                ),
            )
            logger.info("Exercise routine nudge sent to %d for %s", telegram_id, exercise_type)
        except Exception:
            logger.exception("exercise_routine_nudge failed for telegram_id=%s", telegram_id)


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

            # Update eating pattern summary in DB
            pattern_summary = ai.analyze_eating_patterns(meal_history, user_profile)
            database.save_pattern_summary(telegram_id, pattern_summary)

            # Reload profile with the freshly saved pattern
            user_profile = database.get_user(telegram_id)

            # Aggregate weekly stats for the user-facing message
            calorie_stats = database.get_weekly_calorie_stats(telegram_id)
            water_stats = database.get_weekly_water_stats(telegram_id)
            exercise_stats = database.get_weekly_exercise_stats(telegram_id)
            weight_history = database.get_weight_history(telegram_id, days=7)

            calorie_target = user_profile.get("calorie_target", 2000)
            days_on_target = sum(
                1 for cal in calorie_stats["daily"].values() if cal <= calorie_target
            )

            water_goal_ml = _get_water_goal_ml(user_profile)
            water_days_met = sum(
                1 for ml in water_stats["daily"].values() if ml >= water_goal_ml
            )

            weight_start = (
                weight_history[0]["weight_kg"] if weight_history
                else user_profile.get("weight_kg", 0)
            )
            weight_end = (
                weight_history[-1]["weight_kg"] if weight_history
                else user_profile.get("weight_kg", 0)
            )

            weekly_stats = {
                "avg_calories": calorie_stats["avg_calories"],
                "days_on_target": days_on_target,
                "avg_water_ml": water_stats["avg_ml"],
                "water_goal_ml": water_goal_ml,
                "water_days_met": water_days_met,
                "water_days_missed": 7 - water_days_met,
                "exercise_days": exercise_stats["exercise_days"],
                "total_exercise_calories": exercise_stats["total_exercise_calories"],
                "weight_start_kg": weight_start,
                "weight_end_kg": weight_end,
                "weight_change": round(weight_end - weight_start, 1),
            }

            message = ai.generate_weekly_summary(user_profile, weekly_stats)
            await bot.send_message(chat_id=telegram_id, text=message)
            logger.info("Weekly summary sent to user %d", telegram_id)
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


# ── Setup ─────────────────────────────────────────────────────────────────────

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

    # Water nudges: 8am, 12pm, 4pm, 8pm IST = 2:30, 6:30, 10:30, 14:30 UTC
    # Skips users who have already met their daily goal
    _scheduler.add_job(
        _water_nudge,
        CronTrigger(hour="2,6,10,14", minute=30, timezone="UTC"),
        args=[bot],
        id="water_nudge",
    )

    # Medication nudge — 3 windows covering most Indian med schedules:
    # 7:30am IST (02:00 UTC), 1:30pm IST (08:00 UTC), 8:30pm IST (15:00 UTC)
    _scheduler.add_job(
        _medication_routine_nudge,
        CronTrigger(hour="2,8,15", minute=0, timezone="UTC"),
        args=[bot],
        id="medication_routine_nudge",
    )

    # Exercise routine nudge — 6:30pm IST = 13:00 UTC
    # Gives users 2.5h to still log before the 9pm evening summary
    _scheduler.add_job(
        _exercise_routine_nudge,
        CronTrigger(hour=13, minute=0, timezone="UTC"),
        args=[bot],
        id="exercise_routine_nudge",
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

    # Re-engagement: 7pm IST = 13:30 UTC
    _scheduler.add_job(
        _re_engagement,
        CronTrigger(hour=13, minute=30, timezone="UTC"),
        args=[bot],
        id="re_engagement",
    )

    _scheduler.start()
    logger.info(
        "Scheduler started — 7 jobs: morning@03:00, "
        "water@02:30/06:30/10:30/14:30, "
        "medication@02:00/08:00/15:00, exercise_routine@13:00, "
        "evening@15:30, weekly_summary@Sun14:30, re_engagement@13:30 UTC"
    )
    return _scheduler


def shutdown_scheduler() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
