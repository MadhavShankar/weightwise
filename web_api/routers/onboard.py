import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client

from web_api.middleware.auth import verify_token
from web_api.models.schemas import OnboardPayload, ProfilePatch
from services import calculator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["onboard"])


def _sb():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


def _internal_id(auth_uuid: str) -> int:
    sb = _sb()
    row = sb.table("web_users").select("internal_id").eq("auth_uuid", auth_uuid).limit(1).execute()
    if not row.data:
        raise HTTPException(status_code=403, detail="ONBOARDING_INCOMPLETE")
    return row.data[0]["internal_id"]


@router.post("/onboard")
async def onboard(body: OnboardPayload, payload: dict = Depends(verify_token)):
    auth_uuid = payload["sub"]
    internal_id = _internal_id(auth_uuid)
    sb = _sb()

    bmr = calculator.calculate_bmr(body.weight_kg, body.height_cm, body.age, body.gender)
    tdee = calculator.calculate_tdee(bmr, body.activity_level)
    calorie_target = calculator.calculate_calorie_target(tdee)
    macros = calculator.calculate_macros(calorie_target, body.weight_kg)

    sb.table("users").update({
        "name": body.name,
        "age": body.age,
        "gender": body.gender,
        "height_cm": body.height_cm,
        "weight_kg": body.weight_kg,
        "target_weight_kg": body.target_weight_kg,
        "activity_level": body.activity_level,
        "diet_preference": body.diet_preference,
        "medical_conditions": body.medical_conditions,
        "calorie_target": calorie_target,
        "onboarding_complete": True,
        "current_streak": 0,
        "longest_streak": 0,
    }).eq("telegram_id", internal_id).execute()

    logger.info("Onboarded internal_id=%s calorie_target=%s", internal_id, calorie_target)
    return {"calorie_target": calorie_target, "macros": macros}


@router.get("/profile")
async def get_profile(payload: dict = Depends(verify_token)):
    auth_uuid = payload["sub"]
    internal_id = _internal_id(auth_uuid)
    sb = _sb()
    user = sb.table("users").select("*").eq("telegram_id", internal_id).limit(1).execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return user.data[0]


@router.patch("/profile")
async def update_profile(body: ProfilePatch, payload: dict = Depends(verify_token)):
    auth_uuid = payload["sub"]
    internal_id = _internal_id(auth_uuid)
    sb = _sb()

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Recalculate calorie target if relevant fields changed
    recalc_fields = {"weight_kg", "height_cm", "age", "gender", "activity_level"}
    if recalc_fields & set(updates.keys()):
        user = sb.table("users").select("weight_kg,height_cm,age,gender,activity_level").eq("telegram_id", internal_id).limit(1).execute()
        if user.data:
            current = user.data[0]
            w = updates.get("weight_kg", current["weight_kg"])
            h = updates.get("height_cm", current["height_cm"])
            a = updates.get("age", current["age"])
            g = updates.get("gender", current["gender"])
            al = updates.get("activity_level", current["activity_level"])
            if all([w, h, a, g, al]):
                bmr = calculator.calculate_bmr(w, h, a, g)
                tdee = calculator.calculate_tdee(bmr, al)
                updates["calorie_target"] = calculator.calculate_calorie_target(tdee)

    sb.table("users").update(updates).eq("telegram_id", internal_id).execute()
    profile = sb.table("users").select("*").eq("telegram_id", internal_id).limit(1).execute()
    return profile.data[0]
