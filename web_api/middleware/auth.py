import logging
import os
import time
from functools import lru_cache

import httpx
from fastapi import Header, HTTPException
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://uopoejlphsqbzluhxmlp.supabase.co")
_jwks_cache: dict = {}
_jwks_fetched_at: float = 0
_JWKS_TTL = 3600


async def _fetch_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    if _jwks_cache and (time.time() - _jwks_fetched_at) < _JWKS_TTL:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = time.time()
    return _jwks_cache


async def verify_token(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="UNAUTHORIZED")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        jwks = await _fetch_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience="authenticated",
            options={"verify_exp": True},
        )
        return payload
    except JWTError as exc:
        logger.warning("JWT verification failed: %s", exc)
        raise HTTPException(status_code=401, detail="UNAUTHORIZED")
