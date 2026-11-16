import os
from datetime import datetime, timezone
from services import database as db
from services.security import (
    generate_api_key_secret, hash_api_key, key_prefix,
)

DEFAULT_PERMISSIONS = [
    "profile:read", "premium:send", "premium:status",
    "premium:renew", "premium:revoke",
]

async def create_api_key(
    owner_id: str,
    name: str,
    description: str = "",
    permissions: list[str] | None = None,
    expires_at: datetime | None = None,
) -> dict:
    raw_secret = generate_api_key_secret()
    full_key = f"ayaka_live_{raw_secret}"
    key_hash = hash_api_key(raw_secret)
    prefix = key_prefix(raw_secret)
    perms = permissions or DEFAULT_PERMISSIONS

    row = await db.fetchrow(
        """
        INSERT INTO api_keys
            (owner_id, name, description, key_prefix, key_hash, permissions, expires_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, name, description, key_prefix, permissions,
                  status, expires_at, created_at
        """,
        owner_id, name, description, prefix, key_hash, perms, expires_at,
    )
    result = dict(row)
    result["full_key"] = full_key  # HANYA dikembalikan sekali
    return result

async def find_api_key_by_hash(key_hash: str):
    return await db.fetchrow(
        """
        SELECT k.*, u.id AS user_id, u.email AS owner_email, u.is_active AS owner_active
        FROM api_keys k
        JOIN users u ON u.id = k.owner_id
        WHERE k.key_hash = $1
        """,
        key_hash,
    )

async def mark_key_used(key_id: str):
    await db.execute(
        "UPDATE api_keys SET last_used_at = now(), updated_at = now() WHERE id = $1",
        key_id,
    )

async def revoke_key(key_id: str, owner_id: str) -> bool:
    row = await db.fetchrow(
        """
        UPDATE api_keys SET status = 'revoked', updated_at = now()
        WHERE id = $1 AND owner_id = $2 AND status = 'active'
        RETURNING id
        """,
        key_id, owner_id,
    )
    return row is not None

async def list_keys(owner_id: str):
    rows = await db.fetch(
        """
        SELECT id, name, description, key_prefix, permissions,
               status, expires_at, last_used_at, created_at
        FROM api_keys WHERE owner_id = $1
        ORDER BY created_at DESC
        """,
        owner_id,
    )
    return [dict(r) for r in rows]

async def get_key_detail(key_id: str, owner_id: str):
    row = await db.fetchrow(
        """
        SELECT id, name, description, key_prefix, permissions,
               status, expires_at, last_used_at, created_at
        FROM api_keys WHERE id = $1 AND owner_id = $2
        """,
        key_id, owner_id,
    )
    return dict(row) if row else None