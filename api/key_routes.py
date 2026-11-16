from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services import database as db
from services.api_key_service import (
    create_api_key, list_keys, revoke_key, get_key_detail,
    DEFAULT_PERMISSIONS,
)
from api.deps import ok, err, get_current_user, validate_csrf

router = APIRouter(prefix="/api/keys")

class GenerateKeyBody(BaseModel):
    name: str
    description: str = ""
    permissions: list[str] | None = None
    expires_at: datetime | None = None

@router.get("")
async def list_my_keys(user=Depends(get_current_user)):
    keys = await list_keys(str(user["id"]))
    return ok(keys)

@router.post("/generate")
async def generate_key(body: GenerateKeyBody, user=Depends(get_current_user)):
    if not body.name.strip():
        return err("Nama API Key wajib diisi.", "VALIDATION_ERROR", 422)

    perms = body.permissions or DEFAULT_PERMISSIONS
    allowed = set(DEFAULT_PERMISSIONS)
    if not set(perms).issubset(allowed):
        return err("Permission tidak valid.", "INVALID_PERMISSION", 422)

    key = await create_api_key(
        owner_id=str(user["id"]),
        name=body.name.strip(),
        description=body.description.strip(),
        permissions=perms,
        expires_at=body.expires_at,
    )
    # full_key HANYA muncul di response ini
    return ok(key, "API Key berhasil dibuat. Simpan sekarang — tidak akan ditampilkan lagi.", 201)

@router.get("/{key_id}")
async def key_detail(key_id: str, user=Depends(get_current_user)):
    key = await get_key_detail(key_id, str(user["id"]))
    if key is None:
        return err("API Key tidak ditemukan.", "NOT_FOUND", 404)
    return ok(key)

@router.delete("/{key_id}")
async def delete_key(key_id: str, user=Depends(get_current_user)):
    success = await revoke_key(key_id, str(user["id"]))
    if not success:
        return err("API Key tidak ditemukan atau sudah dicabut.", "NOT_FOUND", 404)
    return ok(None, "API Key berhasil dicabut. Key langsung tidak dapat digunakan.")