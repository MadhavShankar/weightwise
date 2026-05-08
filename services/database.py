import logging
import os
from datetime import datetime, timezone, timedelta

from supabase import create_client, Client

logger = logging.getLogger(__name__)

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        _client = create_client(url, key)
    return _client


def get_user(telegram_id: int) -> dict | None:
    client = _get_client()
    result = (
        client.table("users")
        .select("*")
        .eq("telegram_id", telegram_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def create_user(telegram_id: int, name: str) -> dict:
    client = _get_client()
    result = (
        client.table("users")
        .insert({"telegram_id": telegram_id, "name": name})
        .execute()
    )
    return result.data[0]


def update_user(telegram_id: int, updates: dict) -> None:
    client = _get_client()
    client.table("users").update(updates).eq("telegram_id", telegram_id).execute()


def log_meal(
    telegram_id: int,
    description: str,
    calories: int,
    meal_data: dict,
) -> int:
    client = _get_client()
    result = client.table("meal_logs").insert(
        {
            "telegram_id": telegram_id,
            "description": description,
            "calories": calories,
            "meal_data": meal_data,
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()
    return result.data[0]["id"]


def update_meal(meal_id: int, calories: int, meal_data: dict) -> None:
    client = _get_client()
    client.table("meal_logs").update(
        {"calories": calories, "meal_data": meal_data}
    ).eq("id", meal_id).execute()


def get_today_calories(telegram_id: int) -> int:
    client = _get_client()
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    result = (
        client.table("meal_logs")
        .select("calories")
        .eq("telegram_id", telegram_id)
        .gte("logged_at", today_start.isoformat())
        .execute()
    )
    return sum(row["calories"] for row in result.data)


def log_weight(telegram_id: int, weight_kg: float) -> None:
    client = _get_client()
    client.table("weight_logs").insert(
        {
            "telegram_id": telegram_id,
            "weight_kg": weight_kg,
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()


def get_weight_history(telegram_id: int, days: int = 30) -> list:
    client = _get_client()
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = (
        client.table("weight_logs")
        .select("weight_kg, logged_at")
        .eq("telegram_id", telegram_id)
        .gte("logged_at", since.isoformat())
        .order("logged_at", desc=False)
        .execute()
    )
    return result.data


def save_report_summary(telegram_id: int, summary: str) -> None:
    client = _get_client()
    client.table("report_summaries").insert(
        {
            "telegram_id": telegram_id,
            "summary": summary,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()


def get_last_report_summary(telegram_id: int) -> str | None:
    client = _get_client()
    result = (
        client.table("report_summaries")
        .select("summary")
        .eq("telegram_id", telegram_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0]["summary"] if result.data else None


def get_all_onboarded_users() -> list:
    client = _get_client()
    result = (
        client.table("users")
        .select("telegram_id, name, calorie_target, notifications_paused")
        .eq("onboarding_complete", True)
        .execute()
    )
    return [u for u in result.data if not u.get("notifications_paused")]


def get_today_meal_count(telegram_id: int) -> int:
    client = _get_client()
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    result = (
        client.table("meal_logs")
        .select("id")
        .eq("telegram_id", telegram_id)
        .gte("logged_at", today_start.isoformat())
        .execute()
    )
    return len(result.data)


def get_last_meal_logged_at(telegram_id: int) -> datetime | None:
    client = _get_client()
    result = (
        client.table("meal_logs")
        .select("logged_at")
        .eq("telegram_id", telegram_id)
        .order("logged_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return datetime.fromisoformat(result.data[0]["logged_at"])


def get_users_inactive_48h() -> list:
    users = get_all_onboarded_users()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    inactive = []
    for user in users:
        last_logged = get_last_meal_logged_at(user["telegram_id"])
        if last_logged is None or last_logged < cutoff:
            inactive.append(user)
    return inactive


def log_exercise(
    telegram_id: int,
    description: str,
    exercise_type: str,
    duration_min: int,
    calories_burned: int,
) -> int:
    client = _get_client()
    result = client.table("exercise_logs").insert(
        {
            "telegram_id": telegram_id,
            "description": description,
            "exercise_type": exercise_type,
            "duration_min": duration_min,
            "calories_burned": calories_burned,
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()
    return result.data[0]["id"]


def get_today_exercise_calories(telegram_id: int) -> int:
    client = _get_client()
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    result = (
        client.table("exercise_logs")
        .select("calories_burned")
        .eq("telegram_id", telegram_id)
        .gte("logged_at", today_start.isoformat())
        .execute()
    )
    return sum(row["calories_burned"] for row in result.data)


def log_water(telegram_id: int, amount_ml: int) -> None:
    client = _get_client()
    client.table("water_logs").insert(
        {
            "telegram_id": telegram_id,
            "amount_ml": amount_ml,
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()


def get_today_water_ml(telegram_id: int) -> int:
    client = _get_client()
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    result = (
        client.table("water_logs")
        .select("amount_ml")
        .eq("telegram_id", telegram_id)
        .gte("logged_at", today_start.isoformat())
        .execute()
    )
    return sum(row["amount_ml"] for row in result.data)


def log_medication(telegram_id: int, medication_name: str) -> None:
    client = _get_client()
    client.table("medication_logs").insert(
        {
            "telegram_id": telegram_id,
            "medication_name": medication_name,
            "taken_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()


_STREAK_MILESTONES = {3, 7, 14, 30, 60, 90}


def update_streak(telegram_id: int, hit_target: bool) -> dict:
    client = _get_client()
    today = datetime.now(timezone.utc).date().isoformat()

    user = get_user(telegram_id)
    if not user:
        return {"current": 0, "longest": 0, "milestone": None}

    current = user.get("current_streak") or 0
    longest = user.get("longest_streak") or 0
    last_updated = user.get("streak_last_updated")

    if not hit_target:
        client.table("users").update(
            {"current_streak": 0, "streak_last_updated": today}
        ).eq("telegram_id", telegram_id).execute()
        return {"current": 0, "longest": longest, "milestone": None}

    if last_updated == today:
        return {"current": current, "longest": longest, "milestone": None}

    current += 1
    longest = max(longest, current)
    milestone = current if current in _STREAK_MILESTONES else None

    client.table("users").update(
        {
            "current_streak": current,
            "longest_streak": longest,
            "streak_last_updated": today,
        }
    ).eq("telegram_id", telegram_id).execute()

    return {"current": current, "longest": longest, "milestone": milestone}


def get_weekly_meals(telegram_id: int, days: int = 7) -> list:
    client = _get_client()
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = (
        client.table("meal_logs")
        .select("description, calories, meal_data, logged_at")
        .eq("telegram_id", telegram_id)
        .gte("logged_at", since.isoformat())
        .order("logged_at", desc=False)
        .execute()
    )
    return result.data


def save_pattern_summary(telegram_id: int, summary: str) -> None:
    client = _get_client()
    client.table("users").update(
        {
            "eating_pattern_summary": summary,
            "last_pattern_update": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("telegram_id", telegram_id).execute()


def get_medication_schedule(telegram_id: int, medication_name: str) -> dict | None:
    client = _get_client()
    result = (
        client.table("medication_schedules")
        .select("*")
        .eq("telegram_id", telegram_id)
        .ilike("medication_name", medication_name)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def save_medication_schedule(
    telegram_id: int,
    medication_name: str,
    frequency: str,
    schedule_times: str,
) -> None:
    client = _get_client()
    client.table("medication_schedules").insert(
        {
            "telegram_id": telegram_id,
            "medication_name": medication_name,
            "frequency": frequency,
            "schedule_times": schedule_times,
        }
    ).execute()


def get_exercise_routine(telegram_id: int) -> dict | None:
    client = _get_client()
    result = (
        client.table("exercise_routines")
        .select("*")
        .eq("telegram_id", telegram_id)
        .eq("is_active", True)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def save_exercise_routine(
    telegram_id: int,
    exercise_type: str,
    frequency_per_week: int,
    preferred_days: str,
    notes: str = "",
) -> None:
    client = _get_client()
    client.table("exercise_routines").insert(
        {
            "telegram_id": telegram_id,
            "exercise_type": exercise_type,
            "frequency_per_week": frequency_per_week,
            "preferred_days": preferred_days,
            "notes": notes,
        }
    ).execute()


def get_days_since_weight_log(telegram_id: int) -> int | None:
    client = _get_client()
    result = (
        client.table("weight_logs")
        .select("logged_at")
        .eq("telegram_id", telegram_id)
        .order("logged_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    last = datetime.fromisoformat(result.data[0]["logged_at"])
    delta = datetime.now(timezone.utc) - last
    return delta.days
