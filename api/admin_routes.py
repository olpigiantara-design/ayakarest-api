from fastapi import APIRouter, Depends
from datetime import datetime, timezone

from services import database as db
from api.deps import ok, err, require_admin

router = APIRouter(prefix="/api/admin")

@router.get("/overview")
async def overview(admin=Depends(require_admin)):
    users = await db.fetchval("SELECT count(*) FROM users")
    keys = await db.fetchval("SELECT count(*) FROM api_keys")
    requests = await db.fetchval("SELECT count(*) FROM api_request_logs")
    visitors = await db.fetchval(
        "SELECT count(DISTINCT visitor_hash) FROM visitor_analytics"
    )
    premium = await db.fetchval(
        "SELECT count(*) FROM premium_subscriptions WHERE status='active' AND expires_at>now()"
    )
    return ok({
        "total_users": users,
        "total_keys": keys,
        "total_requests": requests,
        "unique_visitors": visitors,
        "active_premium": premium,
    })

@router.get("/users")
async def list_users(admin=Depends(require_admin)):
    rows = await db.fetch(
        """
        SELECT u.id, u.username, u.full_name, u.email, u.role,
               u.is_active, u.created_at,
               (SELECT count(*) FROM api_keys WHERE owner_id=u.id) AS key_count
        FROM users u ORDER BY u.created_at DESC
        """
    )
    return ok([
        {**dict(r), "id": str(r["id"]), "created_at": r["created_at"].isoformat()}
        for r in rows
    ])

@router.post("/users/{user_id}/suspend")
async def suspend_user(user_id: str, admin=Depends(require_admin)):
    if user_id == str(admin["id"]):
        return err("Tidak dapat menangguhkan akun sendiri.", "SELF_ACTION", 400)
    await db.execute("UPDATE users SET is_active=FALSE, updated_at=now() WHERE id=$1", user_id)
    await db.execute("DELETE FROM user_sessions WHERE user_id=$1", user_id)
    return ok(None, "Pengguna ditangguhkan dan semua sesi dicabut.")

@router.post("/users/{user_id}/activate")
async def activate_user(user_id: str, admin=Depends(require_admin)):
    await db.execute("UPDATE users SET is_active=TRUE, updated_at=now() WHERE id=$1", user_id)
    return ok(None, "Pengguna diaktifkan kembali.")

@router.get("/maintenance")
async def get_maintenance(admin=Depends(require_admin)):
    row = await db.fetchrow("SELECT value FROM system_settings WHERE key='maintenance'")
    return ok(row["value"] if row else {"enabled": False})

@router.post("/maintenance")
async def set_maintenance(payload: dict, admin=Depends(require_admin)):
    import json
    enabled = bool(payload.get("enabled"))
    message = str(payload.get("message", "AYAKA API sedang dalam pemeliharaan."))
    value = json.dumps({"enabled": enabled, "message": message})
    await db.execute(
        """
        INSERT INTO system_settings (key, value, updated_at)
        VALUES ('maintenance', $1::jsonb, now())
        ON CONFLICT (key) DO UPDATE SET value=$1::jsonb, updated_at=now()
        """,
        value,
    )
    return ok({"enabled": enabled, "message": message}, "Pengaturan maintenance disimpan.")

@router.get("/audit")
async def audit_logs(admin=Depends(require_admin)):
    rows = await db.fetch(
        """
        SELECT a.id, a.action, a.target_type, a.target_id, a.metadata,
               a.created_at, u.username AS actor
        FROM audit_logs a
        LEFT JOIN users u ON u.id = a.actor_id
        ORDER BY a.created_at DESC LIMIT 100
        """
    )
    return ok([
        {**dict(r), "created_at": r["created_at"].isoformat(),
         "metadata": dict(r["metadata"]) if r["metadata"] else {}}
        for r in rows
    ])