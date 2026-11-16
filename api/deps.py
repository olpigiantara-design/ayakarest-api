import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse

from services import database as db
from services.security import (
    hash_session_token, hash_api_key, hash_ip,
    generate_csrf_token,
)
from services.api_key_service import find_api_key_by_hash, mark_key_used

SESSION_COOKIE = "ayaka_session"
CSRF_COOKIE = "ayaka_csrf"
CSRF_HEADER = "x-csrf-token"

# ---------- Response helpers ----------
def ok(data=None, message="Request successful", status=200):
    return JSONResponse(
        status_code=status,
        content={
            "success": True,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

def err(message: str, code: str, status: int):
    return JSONResponse(
        status_code=status,
        content={
            "success": False,
            "message": message,
            "error": {"code": code},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

# ---------- Session auth ----------
async def get_current_user(request: Request) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="UNAUTHENTICATED")

    session_hash = hash_session_token(token)
    row = await db.fetchrow(
        """
        SELECT s.id AS session_id, s.csrf_token, s.expires_at,
               u.id, u.username, u.full_name, u.email, u.role, u.is_active
        FROM user_sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.session_hash = $1
        """,
        session_hash,
    )
    if row is None:
        raise HTTPException(status_code=401, detail="SESSION_NOT_FOUND")
    if row["expires_at"] < datetime.now(timezone.utc):
        await db.execute("DELETE FROM user_sessions WHERE id = $1", row["session_id"])
        raise HTTPException(status_code=401, detail="SESSION_EXPIRED")
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="ACCOUNT_SUSPENDED")

    await db.execute(
        "UPDATE user_sessions SET last_seen_at = now() WHERE id = $1",
        row["session_id"],
    )
    return dict(row)

async def require_admin(user=Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="ADMIN_ONLY")
    return user

# ---------- CSRF validation ----------
def validate_csrf(request: Request, session_csrf: str):
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    header_token = request.headers.get(CSRF_HEADER)
    if not header_token or not secrets_compare(header_token, session_csrf):
        raise HTTPException(status_code=403, detail="CSRF_INVALID")

def secrets_compare(a: str, b: str) -> bool:
    import hmac
    return hmac.compare_digest(a.encode(), b.encode())

# ---------- API Key auth ----------
async def get_api_key_context(request: Request) -> dict:
    raw = request.headers.get("X-API-Key", "")
    if not raw:
        raise HTTPException(status_code=401, detail="MISSING_API_KEY")
    if not raw.startswith("ayaka_live_"):
        raise HTTPException(status_code=401, detail="INVALID_API_KEY_FORMAT")

    secret = raw[len("ayaka_live_"):]
    key_hash = hash_api_key(secret)
    row = await find_api_key_by_hash(key_hash)
    if row is None:
        raise HTTPException(status_code=401, detail="INVALID_API_KEY")
    if not row["owner_active"]:
        raise HTTPException(status_code=403, detail="OWNER_SUSPENDED")
    if row["status"] == "revoked":
        raise HTTPException(status_code=401, detail="API_KEY_REVOKED")
    if row["status"] == "expired":
        raise HTTPException(status_code=401, detail="API_KEY_EXPIRED")
    if row["expires_at"] and row["expires_at"] < datetime.now(timezone.utc):
        await db.execute(
            "UPDATE api_keys SET status='expired', updated_at=now() WHERE id=$1",
            row["id"],
        )
        raise HTTPException(status_code=401, detail="API_KEY_EXPIRED")

    await mark_key_used(row["id"])

    return {
        "key_id": str(row["id"]),
        "owner_id": str(row["owner_id"]),
        "owner_email": row["owner_email"],
        "permissions": list(row["permissions"]),
        "name": row["name"],
    }

def require_permission(permission: str):
    async def checker(ctx=Depends(get_api_key_context)) -> dict:
        if permission not in ctx["permissions"]:
            raise HTTPException(status_code=403, detail="PERMISSION_DENIED")
        return ctx
    return checker

# ---------- Request logging middleware ----------
async def log_request(
    request: Request,
    status_code: int,
    started_at: float,
    owner_id: Optional[str] = None,
    api_key_id: Optional[str] = None,
):
    import time
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    client_ip = request.client.host if request.client else "0.0.0.0"
    try:
        await db.execute(
            """
            INSERT INTO api_request_logs
                (owner_id, api_key_id, method, endpoint, status_code,
                 response_ms, ip_hash, user_agent)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            """,
            owner_id, api_key_id, request.method,
            request.url.path, status_code, elapsed_ms,
            hash_ip(client_ip),
            (request.headers.get("user-agent") or "")[:300],
        )
    except Exception:
        pass  # logging tidak boleh menggagalkan request utama