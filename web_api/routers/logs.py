import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client

from web_api.middleware.auth import verify_token
from web_api.models.schemas import (
    ExerciseLogRequest,
    MealLogRequest,
    MedicationLogRequest,
    WaterLogRequest,
    WeightLogRequest,
)
from services import ai, database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/log", tags=["logs"])


def _sb():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


def _internal_id(auth_uuid: str) -> int:
    sb = _sb()
    row = sb.table("web_users").select("internal_id").eq("auth_uuid", auth_uuid).limit(1).execute()
    if not row.data:
        raise HTTPException(status_code=403, detail="ONBOARDING_INCOMPLETE")
    return row.data[0]["internal_id"]


@router.post("/meal")
async def log_meal(body: MealLogRequest, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    user = database.get_user(internal_id)
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = await ai.parse_meal(body.description, user)
    meal_id = database.log_meal(internal_id, body.description, result["calories"], result.get("meal_data", {}))
    logger.info("Meal logged internal_id=%s calories=%s", internal_id, result["calories"])
    return {"id": meal_id, "description": body.description, "calories": result["calories"], "meal_data": result.get("meal_data", {})}


@router.post("/weight")
async def log_weight(body: WeightLogRequest, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    database.log_weight(internal_id, body.weight_kg)
    database.update_user(internal_id, {"weight_kg": body.weight_kg})
    logger.info("Weight logged internal_id=%s weight_kg=%s", internal_id, body.weight_kg)
    return {"weight_kg": body.weight_kg, "logged_at": datetime.now(timezone.utc).isoformat()}


@router.post("/water")
async def log_water(body: WaterLogRequest, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    if body.amount_ml:
        ml = body.amount_ml
    elif body.amount_text:
        ml = _parse_water_text(body.amount_text)
    else:
        raise HTTPException(status_code=400, detail="VALIDATION_ERROR")

    database.log_water(internal_id, ml)
    total = database.get_today_water_ml(internal_id)
    user = database.get_user(internal_id)
    goal = (user or {}).get("water_goal_ml") or 2700
    logger.info("Water logged internal_id=%s ml=%s", internal_id, ml)
    return {"amount_ml": ml, "total_today_ml": total, "goal_ml": goal}


def _parse_water_text(text: str) -> int:
    t = text.lower()
    if "glass" in t:
        try:
            count = int("".join(filter(str.isdigit, t)) or "1")
        except ValueError:
            count = 1
        return count * 250
    if "l" in t and "ml" not in t:
        try:
            return int(float("".join(c for c in t if c.isdigit() or c == ".")) * 1000)
        except ValueError:
            pass
    try:
        return int("".join(filter(str.isdigit, t)))
    except ValueError:
        return 250


@router.post("/exercise")
async def log_exercise(body: ExerciseLogRequest, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    user = database.get_user(internal_id)
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = await ai.parse_exercise(body.description, user)
    ex_id = database.log_exercise(
        internal_id,
        body.description,
        result.get("exercise_type", "general"),
        result.get("duration_min", 0),
        result.get("calories_burned", 0),
    )
    logger.info("Exercise logged internal_id=%s calories_burned=%s", internal_id, result.get("calories_burned"))
    return {"id": ex_id, "description": body.description, **result}


@router.post("/medication")
async def log_medication(body: MedicationLogRequest, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    database.log_medication(internal_id, body.text)
    logger.info("Medication logged internal_id=%s", internal_id)
    return {"text": body.text, "logged_at": datetime.now(timezone.utc).isoformat()}
