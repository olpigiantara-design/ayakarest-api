import os
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr

from services import database as db
from services.security import (
    generate_magic_token, hash_magic_token,
)
from services.email_service import (
    send_magic_link_email, send_premium_notification,
)
from api.deps import (
    ok, err, get_api_key_context, require_permission, validate_csrf,
)

router = APIRouter(prefix="/api/am")
BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")
TOKEN_TTL_MINUTES = 15

class SendBody(BaseModel):
    email: EmailStr
    plan: str = "premium"

class RenewBody(BaseModel):
    email: EmailStr
    duration_days: int = 30

class RevokeBody(BaseModel):
    email: EmailStr

# ---------- A. SEND ----------
@router.post("/send")
async def am_send(body: SendBody, ctx=Depends(require_permission("premium:send"))):
    email = body.email.lower()
    if body.plan not in ("premium",):
        return err("Plan tidak didukung.", "INVALID_PLAN", 422)

    token = generate_magic_token()
    token_hash = hash_magic_token(token)
    expires = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_TTL_MINUTES)

    await db.execute(
        """
        INSERT INTO magic_link_tokens
            (api_key_id, owner_id, email, token_hash, plan, expires_at)
        VALUES ($1,$2,$3,$4,$5,$6)
        """,
        ctx["key_id"], ctx["owner_id"], email, token_hash, body.plan, expires,
    )

    try:
        send_magic_link_email(email, token, body.plan, TOKEN_TTL_MINUTES)
    except Exception as exc:
        # Jangan bocorkan detail secret; catat kegagalan tanpa menggagalkan API
        await db.execute(
            """
            INSERT INTO audit_logs (actor_id, action, target_type, target_id, metadata)
            VALUES ($1,'email.send_failed','email',$2,$3::jsonb)
            """,
            ctx["owner_id"], email,
            f'{{"error":"{type(exc).__name__}"}}',
        )
        return err("Gagal mengirim email. Coba lagi nanti.", "EMAIL_SEND_FAILED", 502)

    return ok(
        {"email": email, "expires_in": TOKEN_TTL_MINUTES * 60},
        "Magic Link sent successfully",
    )

# ---------- B. VERIF ----------
@router.get("/verif")
async def am_verif(token: str = Query(...)):
    token_hash = hash_magic_token(token)
    row = await db.fetchrow(
        """
        SELECT * FROM magic_link_tokens
        WHERE token_hash = $1
        """,
        token_hash,
    )
    if row is None:
        return HTMLResponse(_verif_page(False, "Token tidak valid."), status_code=400)
    if row["used_at"] is not None:
        return HTMLResponse(_verif_page(False, "Token sudah digunakan."), status_code=400)
    if row["expires_at"] < datetime.now(timezone.utc):
        return HTMLResponse(_verif_page(False, "Token sudah kedaluwarsa."), status_code=400)

    # Transaksi atomik: tandai token used + aktifkan premium
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            updated = await conn.fetchrow(
                """
                UPDATE magic_link_tokens
                SET used_at = now()
                WHERE id = $1 AND used_at IS NULL
                RETURNING id
                """,
                row["id"],
            )
            if updated is None:
                return HTMLResponse(_verif_page(False, "Token sudah digunakan."), status_code=400)

            new_expires = datetime.now(timezone.utc) + timedelta(days=30)
            await conn.execute(
                """
                INSERT INTO premium_subscriptions
                    (owner_id, email, status, activated_at, expires_at)
                VALUES ($1,$2,'active',now(),$3)
                ON CONFLICT (owner_id, email) DO UPDATE SET
                    status = 'active',
                    activated_at = now(),
                    expires_at = EXCLUDED.expires_at,
                    revoked_at = NULL,
                    updated_at = now()
                """,
                row["owner_id"], row["email"], new_expires,
            )

    try:
        send_premium_notification(
            row["email"],
            "Premium Aktif",
            "Status Premium Anda telah berhasil diaktifkan melalui Magic Link. "
            "Nikmati akses penuh ke fitur premium AYAKA API.",
        )
    except Exception:
        pass

    return HTMLResponse(_verif_page(True, "Premium berhasil diaktifkan."))

def _verif_page(success: bool, message: str) -> str:
    color = "#1a7f37" if success else "#c62828"
    icon = "✓" if success else "✕"
    return f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <title>AYAKA API — Verifikasi</title>
    <style>
      body {{ margin:0; background:#F7F7F2; font-family:Inter,Arial,sans-serif;
             display:flex; align-items:center; justify-content:center; min-height:100vh; }}
      .card {{ background:#fff; border:4px solid #151515; box-shadow:8px 8px 0 #151515;
              border-radius:16px; padding:48px 40px; max-width:460px; text-align:center; }}
      .icon {{ width:64px; height:64px; border-radius:50%; background:{color};
              color:#fff; font-size:32px; line-height:64px; margin:0 auto 20px; font-weight:900; }}
      h1 {{ font-size:22px; color:#151515; margin:0 0 12px; font-weight:900; }}
      p {{ color:#444; line-height:1.6; }}
      a {{ display:inline-block; margin-top:24px; background:#FFD600; color:#151515;
          font-weight:900; text-decoration:none; padding:14px 32px;
          border:3px solid #151515; border-radius:10px; box-shadow:4px 4px 0 #151515; }}
    </style></head><body>
      <div class="card">
        <div class="icon">{icon}</div>
        <h1>{'Verifikasi Berhasil' if success else 'Verifikasi Gagal'}</h1>
        <p>{message}</p>
        <a href="/dashboard">KE DASHBOARD</a>
      </div>
    </body></html>
    """

# ---------- C. STATUS ----------
@router.get("/status")
async def am_status(email: str = Query(...), ctx=Depends(require_permission("premium:status"))):
    row = await db.fetchrow(
        """
        SELECT status, expires_at FROM premium_subscriptions
        WHERE owner_id = $1 AND lower(email) = lower($2)
        """,
        ctx["owner_id"], email,
    )
    if row is None:
        return ok({
            "email": email, "premium": False,
            "status": "none", "expires_at": None,
        })
    now = datetime.now(timezone.utc)
    if row["status"] == "active" and row["expires_at"] < now:
        await db.execute(
            "UPDATE premium_subscriptions SET status='expired', updated_at=now() "
            "WHERE owner_id=$1 AND lower(email)=lower($2)",
            ctx["owner_id"], email,
        )
        return ok({
            "email": email, "premium": False,
            "status": "expired", "expires_at": row["expires_at"].isoformat(),
        })
    return ok({
        "email": email,
        "premium": row["status"] == "active",
        "status": row["status"],
        "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
    })

# ---------- D. RENEW ----------
@router.post("/renew")
async def am_renew(body: RenewBody, ctx=Depends(require_permission("premium:renew"))):
    if body.duration_days < 1 or body.duration_days > 3650:
        return err("Durasi harus antara 1 dan 3650 hari.", "INVALID_DURATION", 422)

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            sub = await conn.fetchrow(
                """
                SELECT id, expires_at, status FROM premium_subscriptions
                WHERE owner_id = $1 AND lower(email) = lower($2)
                FOR UPDATE
                """,
                ctx["owner_id"], body.email.lower(),
            )
            if sub is None:
                return err("Langganan tidak ditemukan.", "NOT_FOUND", 404)

            now = datetime.now(timezone.utc)
            base = sub["expires_at"] if sub["expires_at"] > now else now
            new_expires = base + timedelta(days=body.duration_days)

            await conn.execute(
                """
                UPDATE premium_subscriptions
                SET status='active', expires_at=$1, revoked_at=NULL, updated_at=now()
                WHERE id=$2
                """,
                new_expires, sub["id"],
            )
            await conn.execute(
                """
                INSERT INTO premium_renewal_logs
                    (subscription_id, api_key_id, old_expires_at,
                     new_expires_at, duration_days)
                VALUES ($1,$2,$3,$4,$5)
                """,
                sub["id"], ctx["key_id"], sub["expires_at"],
                new_expires, body.duration_days,
            )

    try:
        send_premium_notification(
            body.email, "Premium Diperpanjang",
            f"Masa berlaku Premium Anda diperpanjang {body.duration_days} hari. "
            f"Berlaku hingga {new_expires.strftime('%d %b %Y %H:%M UTC')}.",
        )
    except Exception:
        pass

    return ok({
        "email": body.email,
        "expires_at": new_expires.isoformat(),
        "duration_days": body.duration_days,
    }, "Premium berhasil diperpanjang.")

# ---------- E. REVOKE ----------
@router.post("/revoke")
async def am_revoke(body: RevokeBody, ctx=Depends(require_permission("premium:revoke"))):
    row = await db.fetchrow(
        """
        UPDATE premium_subscriptions
        SET status='revoked', revoked_at=now(), updated_at=now()
        WHERE owner_id=$1 AND lower(email)=lower($2)
          AND status IN ('active','expired')
        RETURNING id
        """,
        ctx["owner_id"], body.email.lower(),
    )
    if row is None:
        return err("Langganan aktif tidak ditemukan.", "NOT_FOUND", 404)

    await db.execute(
        """
        INSERT INTO audit_logs (actor_id, action, target_type, target_id, metadata)
        VALUES ($1,'premium.revoke','email',$2,$3::jsonb)
        """,
        ctx["owner_id"], body.email,
        f'{{"api_key_id":"{ctx["key_id"]}"}}',
    )

    try:
        send_premium_notification(
            body.email, "Premium Dicabut",
            "Status Premium akun Anda telah dicabut oleh administrator aplikasi.",
        )
    except Exception:
        pass

    return ok({"email": body.email, "status": "revoked"}, "Premium berhasil dicabut.")