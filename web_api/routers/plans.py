import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from supabase import create_client

from web_api.middleware.auth import verify_token
from services import ai, database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["plans"])


def _sb():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


def _internal_id(auth_uuid: str) -> int:
    sb = _sb()
    row = sb.table("web_users").select("internal_id").eq("auth_uuid", auth_uuid).limit(1).execute()
    if not row.data:
        raise HTTPException(status_code=403, detail="ONBOARDING_INCOMPLETE")
    return row.data[0]["internal_id"]


@router.get("/plan")
async def get_plan(payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    user = database.get_user(internal_id)
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"plan": user.get("current_plan") or ""}


@router.post("/plan/generate")
async def generate_plan(payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    user = database.get_user(internal_id)
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")

    plan = await ai.generate_plan(user)
    database.update_user(internal_id, {"current_plan": plan})
    logger.info("Plan generated internal_id=%s", internal_id)
    return {"plan": plan}


@router.get("/mealplan")
async def get_meal_plan(payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    sb = _sb()
    user_row = sb.table("users").select("meal_plan").eq("telegram_id", internal_id).limit(1).execute()
    meal_plan = (user_row.data[0].get("meal_plan") or "") if user_row.data else ""
    return {"meal_plan": meal_plan}


@router.post("/mealplan/generate")
async def generate_meal_plan(payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    user = database.get_user(internal_id)
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")

    meal_plan = await ai.generate_meal_plan(user)
    _sb().table("users").update({"meal_plan": meal_plan}).eq("telegram_id", internal_id).execute()
    logger.info("Meal plan generated internal_id=%s", internal_id)
    return {"meal_plan": meal_plan}


@router.post("/report/analyze")
async def analyze_report(payload: dict = Depends(verify_token), file: UploadFile = File(...)):
    if file.content_type not in ("image/jpeg", "image/png", "application/pdf"):
        raise HTTPException(status_code=415, detail="UNSUPPORTED_FILE_TYPE")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="FILE_TOO_LARGE")

    internal_id = _internal_id(payload["sub"])
    user = database.get_user(internal_id)
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = await ai.analyse_report(content, file.content_type, user)
    database.save_report_summary(internal_id, result["summary"])
    return result


@router.get("/report/latest")
async def latest_report(payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    summary = database.get_last_report_summary(internal_id)
    return {"summary": summary or ""}


@router.get("/tests/recommend")
async def test_recommendations(payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    user = database.get_user(internal_id)
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")
    recs = await ai.generate_test_recommendations(user)
    return {"recommendations": recs}
