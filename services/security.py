import os
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,   # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

API_KEY_PEPPER = os.environ.get("API_KEY_PEPPER", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "")

# ---------- Password ----------
def hash_password(password: str) -> str:
    return _ph.hash(password)

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return _ph.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False

# ---------- API Key ----------
def generate_api_key_secret() -> str:
    """Menghasilkan secret acak kriptografis 32 byte (43 char base64url)."""
    return secrets.token_urlsafe(32)

def hash_api_key(secret: str) -> str:
    """SHA-256(pepper + secret). Pepper disimpan hanya di server."""
    return hashlib.sha256((API_KEY_PEPPER + secret).encode()).hexdigest()

def key_prefix(secret: str) -> str:
    """6 karakter pertama setelah ayaka_live_ untuk display."""
    return "ayaka_live_" + secret[:6]

# ---------- Session ----------
def generate_session_token() -> str:
    return secrets.token_urlsafe(48)

def hash_session_token(token: str) -> str:
    return hmac.new(
        SESSION_SECRET.encode(), token.encode(), hashlib.sha256
    ).hexdigest()

def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)

# ---------- IP anonymization ----------
def hash_ip(ip: str) -> str:
    return hashlib.sha256((SESSION_SECRET + ip).encode()).hexdigest()[:32]

# ---------- Magic link token ----------
def generate_magic_token() -> str:
    return secrets.token_urlsafe(32)

def hash_magic_token(token: str) -> str:
    return hashlib.sha256((API_KEY_PEPPER + token).encode()).hexdigest()