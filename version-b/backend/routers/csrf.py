"""CSRF protection: stateless HMAC double-submit token."""
import hashlib
import hmac
import os
import secrets
import time

from fastapi import APIRouter, Header, HTTPException

CSRF_SECRET = os.getenv("CSRF_SECRET", secrets.token_hex(32))
CSRF_TTL = 300  # 5 minutes

router = APIRouter(tags=["csrf"])


def make_csrf_token() -> str:
    expire = str(int(time.time()) + CSRF_TTL)
    sig = hmac.new(CSRF_SECRET.encode(), expire.encode(), hashlib.sha256).hexdigest()
    return f"{expire}:{sig}"


def verify_csrf_token(token: str) -> bool:
    try:
        expire_str, sig = token.split(":", 1)
        if int(time.time()) > int(expire_str):
            return False
        expected = hmac.new(CSRF_SECRET.encode(), expire_str.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)
    except Exception:
        return False


async def require_csrf(x_csrf_token: str | None = Header(None, alias="X-CSRF-Token")) -> None:
    if not x_csrf_token or not verify_csrf_token(x_csrf_token):
        raise HTTPException(status_code=403, detail="CSRF check failed")


@router.get("/csrf/token")
async def get_csrf_token() -> dict:
    return {"token": make_csrf_token(), "ttl": CSRF_TTL}
