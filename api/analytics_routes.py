from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta, timezone

from services import database as db
from api.deps import ok, get_current_user, get_api_key_context

router = APIRouter(prefix="/api")

@router.get("/analytics")
async def analytics(user=Depends(get_current_user)):
    uid = str(user["id"])
    total_req = await db.fetchval(
        "SELECT count(*) FROM api_request_logs WHERE owner_id=$1", uid
    )
    total_keys = await db.fetchval(
        "SELECT count(*) FROM api_keys WHERE owner_id=$1", uid
    )
    active_keys = await db.fetchval(
        "SELECT count(*) FROM api_keys WHERE owner_id=$1 AND status='active'", uid
    )
    revoked_keys = await db.fetchval(
        "SELECT count(*) FROM api_keys WHERE owner_id=$1 AND status='revoked'", uid
    )
    success_req = await db.fetchval(
        "SELECT count(*) FROM api_request_logs WHERE owner_id=$1 AND status_code < 400", uid
    )
    failed_req = await db.fetchval(
        "SELECT count(*) FROM api_request_logs WHERE owner_id=$1 AND status_code >= 400", uid
    )
    premium_active = await db.fetchval(
        "SELECT count(*) FROM premium_subscriptions WHERE owner_id=$1 "
        "AND status='active' AND expires_at > now()", uid
    )
    emails_sent = await db.fetchval(
        "SELECT count(*) FROM magic_link_tokens WHERE owner_id=$1", uid
    )

    # Grafik 24 jam terakhir
    rows = await db.fetch(
        """
        SELECT date_trunc('hour', created_at) AS bucket,
               count(*) FILTER (WHERE status_code < 400) AS success,
               count(*) FILTER (WHERE status_code >= 400) AS failed,
               count(*) AS total
        FROM api_request_logs
        WHERE owner_id=$1 AND created_at > now() - interval '24 hours'
        GROUP BY 1 ORDER BY 1
        """,
        uid,
    )
    hourly = [
        {
            "hour": r["bucket"].isoformat(),
            "success": r["success"],
            "failed": r["failed"],
            "total": r["total"],
        }
        for r in rows
    ]

    return ok({
        "total_requests": total_req,
        "total_keys": total_keys,
        "active_keys": active_keys,
        "revoked_keys": revoked_keys,
        "success_requests": success_req,
        "failed_requests": failed_req,
        "premium_active": premium_active,
        "emails_sent": emails_sent,
        "hourly": hourly,
        "server_time": datetime.now(timezone.utc).isoformat(),
    })

@router.get("/logs")
async def logs(
    user=Depends(get_current_user),
    endpoint: str | None = None,
    status: int | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
):
    uid = str(user["id"])
    where = ["owner_id = $1"]
    args = [uid]
    idx = 2
    if endpoint:
        where.append(f"endpoint ILIKE ${idx}")
        args.append(f"%{endpoint}%")
        idx += 1
    if status:
        where.append(f"status_code = ${idx}")
        args.append(status)
        idx += 1
    where_sql = " AND ".join(where)
    offset = (page - 1) * per_page

    total = await db.fetchval(
        f"SELECT count(*) FROM api_request_logs WHERE {where_sql}", *args
    )
    rows = await db.fetch(
        f"""
        SELECT id, method, endpoint, status_code, response_ms,
               created_at, api_key_id
        FROM api_request_logs
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT {per_page} OFFSET {offset}
        """,
        *args,
    )
    return ok({
        "logs": [
            {
                **dict(r),
                "created_at": r["created_at"].isoformat(),
                "api_key_id": str(r["api_key_id"]) if r["api_key_id"] else None,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    })

@router.get("/health")
async def health():
    db_ok = True
    try:
        await db.fetchval("SELECT 1")
    except Exception:
        db_ok = False
    return ok({
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "server_time": datetime.now(timezone.utc).isoformat(),
    })

@router.get("/user/profile")
async def api_profile(ctx=Depends(get_api_key_context)):
    row = await db.fetchrow(
        "SELECT username, full_name, email, created_at FROM users WHERE id=$1",
        ctx["owner_id"],
    )
    return ok({
        "username": row["username"],
        "full_name": row["full_name"],
        "email": row["email"],
        "member_since": row["created_at"].isoformat(),
        "api_key_name": ctx["name"],
        "permissions": ctx["permissions"],
    })