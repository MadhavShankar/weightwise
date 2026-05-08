import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client

from web_api.middleware.auth import verify_token

router = APIRouter(prefix="/api", tags=["today"])


def _sb():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


def _internal_id(auth_uuid: str) -> int:
    sb = _sb()
    row = sb.table("web_users").select("internal_id").eq("auth_uuid", auth_uuid).limit(1).execute()
    if not row.data:
        raise HTTPException(status_code=403, detail="ONBOARDING_INCOMPLETE")
    return row.data[0]["internal_id"]


@router.get("/today/summary")
async def today_summary(payload: dict = Depends(verify_token)):
    auth_uuid = payload["sub"]
    internal_id = _internal_id(auth_uuid)
    sb = _sb()

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    user = sb.table("users").select(
        "calorie_target,water_goal_ml,current_streak,name"
    ).eq("telegram_id", internal_id).limit(1).execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    u = user.data[0]

    meals = sb.table("meal_logs").select(
        "id,description,calories,logged_at"
    ).eq("telegram_id", internal_id).gte("logged_at", today_start).order("logged_at").execute()

    water = sb.table("water_logs").select("amount_ml").eq("telegram_id", internal_id).gte("logged_at", today_start).execute()

    exercise = sb.table("exercise_logs").select("calories_burned").eq("telegram_id", internal_id).gte("logged_at", today_start).execute()

    calories_consumed = sum(m["calories"] for m in meals.data)
    water_ml = sum(w["amount_ml"] for w in water.data)
    exercise_burned = sum(e["calories_burned"] for e in exercise.data)

    return {
        "name": u["name"],
        "calories_consumed": calories_consumed,
        "calorie_target": u["calorie_target"] or 0,
        "water_ml": water_ml,
        "water_goal_ml": u.get("water_goal_ml") or 2700,
        "exercise_calories_burned": exercise_burned,
        "streak": u.get("current_streak") or 0,
        "meals": meals.data,
    }
