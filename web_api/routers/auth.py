from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client

from web_api.middleware.auth import verify_token
from web_api.models.schemas import LinkByPhoneRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_DOMAIN = "@ww.weightwise.in"


def _get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    return create_client(url, key)


def _phone_from_email(email: str) -> str | None:
    """Extract phone from synthetic email like +919876543210@ww.weightwise.in"""
    if email and email.endswith(EMAIL_DOMAIN):
        candidate = email[: -len(EMAIL_DOMAIN)]
        if candidate.startswith("+"):
            return candidate
    return None


def _ensure_web_user(auth_uuid: str, email: str | None = None) -> int:
    """Return existing internal_id, or create and optionally auto-link a new web_users row."""
    sb = _get_supabase()

    row = sb.table("web_users").select("internal_id").eq("auth_uuid", auth_uuid).limit(1).execute()
    if row.data:
        return row.data[0]["internal_id"]

    phone = _phone_from_email(email or "")

    # If the phone matches an existing Telegram user, link directly
    if phone:
        tg_user = sb.table("users").select("telegram_id").eq("phone_number", phone).limit(1).execute()
        if tg_user.data:
            tg_id = tg_user.data[0]["telegram_id"]
            sb.table("web_users").insert({
                "auth_uuid": auth_uuid,
                "internal_id": tg_id,
                "email": email,
                "phone_number": phone,
            }).execute()
            logger.info("Auto-linked auth_uuid=%s to telegram_id=%s via phone", auth_uuid, tg_id)
            return tg_id

    # New mobile-only user
    seq = sb.rpc("nextval", {"sequence_name": "web_user_id_seq"}).execute()
    internal_id = seq.data

    sb.table("users").insert({
        "telegram_id": internal_id,
        "name": "New User",
        "phone_number": phone,
    }).execute()
    sb.table("web_users").insert({
        "auth_uuid": auth_uuid,
        "internal_id": internal_id,
        "email": email,
        "phone_number": phone,
    }).execute()
    logger.info("Created new web user auth_uuid=%s internal_id=%s", auth_uuid, internal_id)
    return internal_id


@router.get("/me")
async def get_me(payload: dict = Depends(verify_token)):
    auth_uuid = payload["sub"]
    email = payload.get("email", "")

    internal_id = _ensure_web_user(auth_uuid, email)

    sb = _get_supabase()
    user = sb.table("users").select("onboarding_complete").eq("telegram_id", internal_id).limit(1).execute()
    onboarded = user.data[0]["onboarding_complete"] if user.data else False
    return {"internal_id": internal_id, "onboarding_complete": onboarded}


@router.post("/link-by-phone")
async def link_by_phone(body: LinkByPhoneRequest, payload: dict = Depends(verify_token)):
    auth_uuid = payload["sub"]
    phone = body.phone_number
    sb = _get_supabase()

    tg_user = sb.table("users").select("telegram_id, name").eq("phone_number", phone).limit(1).execute()

    web_row = sb.table("web_users").select("internal_id").eq("auth_uuid", auth_uuid).limit(1).execute()
    if not web_row.data:
        raise HTTPException(status_code=400, detail="Web user row not found — call /me first")

    temp_internal_id = web_row.data[0]["internal_id"]

    if tg_user.data:
        tg_id = tg_user.data[0]["telegram_id"]
        sb.table("web_users").update({"internal_id": tg_id, "phone_number": phone}).eq("auth_uuid", auth_uuid).execute()
        if temp_internal_id != tg_id:
            sb.table("users").delete().eq("telegram_id", temp_internal_id).execute()
        profile = sb.table("users").select("*").eq("telegram_id", tg_id).limit(1).execute()
        logger.info("Linked auth_uuid=%s to telegram_id=%s", auth_uuid, tg_id)
        return {"linked": True, "profile": profile.data[0] if profile.data else None}

    sb.table("web_users").update({"phone_number": phone}).eq("auth_uuid", auth_uuid).execute()
    sb.table("users").update({"phone_number": phone}).eq("telegram_id", temp_internal_id).execute()
    return {"linked": False}
