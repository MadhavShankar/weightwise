import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client

from web_api.middleware.auth import verify_token
from web_api.models.schemas import DeviceTokenRequest, NotificationsReadRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["notifications"])


def _sb():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


def _internal_id(auth_uuid: str) -> int:
    sb = _sb()
    row = sb.table("web_users").select("internal_id").eq("auth_uuid", auth_uuid).limit(1).execute()
    if not row.data:
        raise HTTPException(status_code=403, detail="ONBOARDING_INCOMPLETE")
    return row.data[0]["internal_id"]


@router.get("/notifications")
async def list_notifications(unread_only: bool = True, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    sb = _sb()
    query = sb.table("notifications").select("*").eq("internal_id", internal_id).order("created_at", desc=True)
    if unread_only:
        query = query.eq("is_read", False)
    result = query.execute()
    return result.data


@router.post("/notifications/read")
async def mark_read(body: NotificationsReadRequest, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    sb = _sb()
    sb.table("notifications").update({"is_read": True}).eq("internal_id", internal_id).in_("id", body.ids).execute()
    return {"ok": True}


@router.post("/devices")
async def register_device(body: DeviceTokenRequest, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    sb = _sb()
    sb.table("device_tokens").upsert({
        "internal_id": internal_id,
        "expo_token": body.expo_push_token,
        "platform": body.platform,
    }, on_conflict="internal_id,expo_token").execute()
    logger.info("Device registered internal_id=%s platform=%s", internal_id, body.platform)
    return {"ok": True}
