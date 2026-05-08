import os
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client

from web_api.middleware.auth import verify_token

router = APIRouter(prefix="/api/history", tags=["history"])


def _sb():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


def _internal_id(auth_uuid: str) -> int:
    sb = _sb()
    row = sb.table("web_users").select("internal_id").eq("auth_uuid", auth_uuid).limit(1).execute()
    if not row.data:
        raise HTTPException(status_code=403, detail="ONBOARDING_INCOMPLETE")
    return row.data[0]["internal_id"]


@router.get("/meals")
async def meal_history(days: int = 7, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    sb = _sb()
    result = sb.table("meal_logs").select(
        "id,description,calories,meal_data,logged_at"
    ).eq("telegram_id", internal_id).gte("logged_at", since).order("logged_at", desc=True).execute()
    return result.data


@router.get("/weight")
async def weight_history(days: int = 30, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    sb = _sb()
    result = sb.table("weight_logs").select(
        "id,weight_kg,logged_at"
    ).eq("telegram_id", internal_id).gte("logged_at", since).order("logged_at").execute()

    user = sb.table("users").select("weight_kg,target_weight_kg").eq("telegram_id", internal_id).limit(1).execute()
    start_weight = result.data[0]["weight_kg"] if result.data else None
    current_weight = user.data[0]["weight_kg"] if user.data else None
    target_weight = user.data[0]["target_weight_kg"] if user.data else None

    return {
        "entries": result.data,
        "start_weight": start_weight,
        "current_weight": current_weight,
        "target_weight": target_weight,
    }


@router.get("/exercise")
async def exercise_history(days: int = 7, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    sb = _sb()
    result = sb.table("exercise_logs").select(
        "id,description,exercise_type,duration_min,calories_burned,logged_at"
    ).eq("telegram_id", internal_id).gte("logged_at", since).order("logged_at", desc=True).execute()
    return result.data


@router.get("/water")
async def water_history(days: int = 7, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    sb = _sb()
    result = sb.table("water_logs").select(
        "amount_ml,logged_at"
    ).eq("telegram_id", internal_id).gte("logged_at", since).execute()

    user = sb.table("users").select("water_goal_ml").eq("telegram_id", internal_id).limit(1).execute()
    goal = (user.data[0].get("water_goal_ml") if user.data else None) or 2700

    daily: dict[str, int] = {}
    for row in result.data:
        day = row["logged_at"][:10]
        daily[day] = daily.get(day, 0) + row["amount_ml"]

    return [{"date": d, "amount_ml": v, "goal_ml": goal} for d, v in sorted(daily.items())]
