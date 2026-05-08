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
) -> None:
    client = _get_client()
    client.table("meal_logs").insert(
        {
            "telegram_id": telegram_id,
            "description": description,
            "calories": calories,
            "meal_data": meal_data,
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()


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
