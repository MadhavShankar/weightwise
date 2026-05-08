from __future__ import annotations

import json
import logging
import os
import sys
from typing import AsyncGenerator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from supabase import create_client

from web_api.middleware.auth import verify_token
from web_api.models.schemas import ChatRequest, MealCorrectRequest, RestaurantRequest
from services import ai, database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


def _sb():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


def _internal_id(auth_uuid: str) -> int:
    sb = _sb()
    row = sb.table("web_users").select("internal_id").eq("auth_uuid", auth_uuid).limit(1).execute()
    if not row.data:
        raise HTTPException(status_code=403, detail="ONBOARDING_INCOMPLETE")
    return row.data[0]["internal_id"]


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _stream_coach_reply(internal_id: int, message: str, image_bytes: bytes | None = None) -> AsyncGenerator[str, None]:
    user = database.get_user(internal_id)
    if not user:
        yield _sse("error", {"code": "PROFILE_NOT_FOUND", "message": "Profile not found"})
        return

    try:
        async for chunk in ai.stream_coach_reply(message, user, image_bytes=image_bytes):
            event_type = chunk.get("type", "token")
            if event_type == "token":
                yield _sse("token", {"text": chunk["text"]})
            elif event_type == "meal_logged":
                yield _sse("meal_logged", chunk["data"])
            elif event_type == "done":
                yield _sse("done", {})
                return
    except Exception as exc:
        logger.error("SSE stream error internal_id=%s: %s", internal_id, exc)
        yield _sse("error", {"code": "AI_UNAVAILABLE", "message": "Coach is temporarily unavailable."})


@router.post("/chat")
async def chat(body: ChatRequest, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    logger.info("Chat request internal_id=%s", internal_id)
    return StreamingResponse(
        _stream_coach_reply(internal_id, body.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat/photo")
async def chat_photo(payload: dict = Depends(verify_token), file: UploadFile = File(...)):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=415, detail="UNSUPPORTED_FILE_TYPE")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="FILE_TOO_LARGE")

    internal_id = _internal_id(payload["sub"])
    return StreamingResponse(
        _stream_coach_reply(internal_id, "Analyse this meal photo and log what you see.", image_bytes=content),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat/report")
async def chat_report(payload: dict = Depends(verify_token), file: UploadFile = File(...)):
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


@router.post("/meal/correct")
async def correct_meal(body: MealCorrectRequest, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    user = database.get_user(internal_id)
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = await ai.parse_meal(body.correction, user)
    database.update_meal(body.meal_id, result["calories"], result.get("meal_data", {}))
    return {"meal_id": body.meal_id, "calories": result["calories"], "meal_data": result.get("meal_data", {})}


@router.post("/restaurant")
async def restaurant(body: RestaurantRequest, payload: dict = Depends(verify_token)):
    internal_id = _internal_id(payload["sub"])
    user = database.get_user(internal_id)
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")

    async def _stream():
        try:
            async for chunk in ai.stream_restaurant_advice(body.place_name, user):
                if chunk.get("type") == "token":
                    yield _sse("token", {"text": chunk["text"]})
                elif chunk.get("type") == "done":
                    yield _sse("done", {})
                    return
        except Exception as exc:
            logger.error("Restaurant stream error: %s", exc)
            yield _sse("error", {"code": "AI_UNAVAILABLE", "message": "Unavailable."})

    return StreamingResponse(_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
