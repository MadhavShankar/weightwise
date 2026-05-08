import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client

from web_api.middleware.auth import verify_token
from web_api.models.schemas import ExerciseRoutinePayload, MedicationSchedulePayload, NotificationsSettingRequest
from services import database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["routines"])


def _sb():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


def _internal_id(auth_uuid: str) -> int:
    sb = _sb()
    row = sb.table("web_users").select("internal_id").eq("auth_uuid", auth_uuid).limit(1).execute()
    if not row.data:
        raise HTTPException(status_code=403, detail="ONBOARDING_INCOMPLETE")
    return row.data[0]["internal_id"]


@router.get("/routines/exercise")
async def get_exercise_routine(payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    return database.get_exercise_routine(internal_id)


@router.post("/routines/exercise")
async def set_exercise_routine(body: ExerciseRoutinePayload, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    database.save_exercise_routine(
        internal_id, body.exercise_type, body.frequency_per_week, body.preferred_days, body.notes or ""
    )
    return database.get_exercise_routine(internal_id)


@router.get("/routines/medication")
async def get_medication_schedules(payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    sb = _sb()
    result = sb.table("medication_schedules").select("*").eq("telegram_id", internal_id).eq("is_active", True).execute()
    return result.data


@router.post("/routines/medication")
async def add_medication_schedule(body: MedicationSchedulePayload, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    database.save_medication_schedule(
        internal_id, body.medication_name, body.frequency, body.schedule_times
    )
    sb = _sb()
    result = sb.table("medication_schedules").select("*").eq("telegram_id", internal_id).order("id", desc=True).limit(1).execute()
    return result.data[0] if result.data else {}


@router.patch("/settings/notifications")
async def update_notification_settings(body: NotificationsSettingRequest, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    database.update_user(internal_id, {"notifications_paused": body.paused})
    return {"paused": body.paused}
