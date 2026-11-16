import os
import re
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, Response, Depends, HTTPException
from pydantic import BaseModel, EmailStr, field_validator

from services import database as db
from services.security import (
    hash_password, verify_password, generate_session_token,
    hash_session_token, generate_csrf_token, hash_ip,
)
from api.deps import (
    ok, err, get_current_user, SESSION_COOKIE, CSRF_COOKIE,
    validate_csrf,
)

router = APIRouter(prefix="/api/auth")

SESSION_DAYS = 7
SESSION_DAYS_REMEMBER = 30

class RegisterBody(BaseModel):
    username: str
    full_name: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        if not re.fullmatch(r"[a-zA-Z0-9_]{3,40}", v):
            raise ValueError("Username harus 3-40 karakter alfanumerik/underscore.")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v):
        if len(v) < 8:
            raise ValueError("Password minimal 8 karakter.")
        if not re.search(r"[A-Z]", v) or not re.search(r"[0-9]", v):
            raise ValueError("Password harus mengandung huruf besar dan angka.")
        return v

class LoginBody(BaseModel):
    email: EmailStr
    password: str
    remember: bool = False

@router.post("/register")
async def register(body: RegisterBody):
    existing = await db.fetchval(
        "SELECT id FROM users WHERE lower(email) = lower($1)", body.email
    )
    if existing:
        return err("Email sudah terdaftar.", "EMAIL_DUPLICATE", 409)

    username_taken = await db.fetchval(
        "SELECT id FROM users WHERE lower(username) = lower($1)", body.username
    )
    if username_taken:
        return err("Username sudah digunakan.", "USERNAME_DUPLICATE", 409)

    pw_hash = hash_password(body.password)
    row = await db.fetchrow(
        """
        INSERT INTO users (username, full_name, email, password_hash)
        VALUES ($1,$2,$3,$4)
        RETURNING id, username, full_name, email, role, created_at
        """,
        body.username, body.full_name, body.email.lower(), pw_hash,
    )
    return ok(dict(row), "Registrasi berhasil. Silakan login.", 201)

@router.post("/login")
async def login(body: LoginBody, request: Request, response: Response):
    row = await db.fetchrow(
        "SELECT * FROM users WHERE lower(email) = lower($1)", body.email
    )
    if row is None or not verify_password(body.password, row["password_hash"]):
        return err("Email atau password salah.", "INVALID_CREDENTIALS", 401)
    if not row["is_active"]:
        return err("Akun ditangguhkan.", "ACCOUNT_SUSPENDED", 403)

    token = generate_session_token()
    token_hash = hash_session_token(token)
    csrf = generate_csrf_token()
    days = SESSION_DAYS_REMEMBER if body.remember else SESSION_DAYS
    expires = datetime.now(timezone.utc) + timedelta(days=days)

    await db.execute(
        """
        INSERT INTO user_sessions
            (user_id, session_hash, csrf_token, user_agent, ip_hash, expires_at)
        VALUES ($1,$2,$3,$4,$5,$6)
        """,
        row["id"], token_hash, csrf,
        (request.headers.get("user-agent") or "")[:300],
        hash_ip(request.client.host if request.client else "0.0.0.0"),
        expires,
    )

    response.set_cookie(
        key=SESSION_COOKIE, value=token,
        httponly=True, secure=True, samesite="lax",
        max_age=days * 86400, path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE, value=csrf,
        httponly=False, secure=True, samesite="lax",
        max_age=days * 86400, path="/",
    )
    return ok(
        {"username": row["username"], "email": row["email"], "role": row["role"]},
        "Login berhasil.",
    )

@router.post("/logout")
async def logout(request: Request, response: Response, user=Depends(get_current_user)):
    validate_csrf(request, user["csrf_token"])
    await db.execute("DELETE FROM user_sessions WHERE id = $1", user["session_id"])
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return ok(None, "Logout berhasil.")

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return ok({
        "id": str(user["id"]),
        "username": user["username"],
        "full_name": user["full_name"],
        "email": user["email"],
        "role": user["role"],
    })