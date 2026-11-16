import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import time

from api.auth_routes import router as auth_router
from api.key_routes import router as key_router
from api.magic_link_routes import router as magic_router
from api.analytics_routes import router as analytics_router
from api.admin_routes import router as admin_router
from api.deps import log_request, get_current_user
from services import database as db

BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await db.close_pool()

app = FastAPI(
    title="AYAKA API",
    version="1.0.0",
    description="REST API Management Platform — Powered by AYAKA Sync",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[BASE_URL] if BASE_URL else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-CSRF-Token"],
)

# ---------- Request logging middleware ----------
@app.middleware("http")
async def request_logger(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    # Hanya log endpoint /api/* yang bukan health & static
    if request.url.path.startswith("/api/") and request.url.path != "/api/health":
        owner_id = None
        key_id = None
        try:
            # Coba ambil konteks API key dari state jika ada
            ctx = getattr(request.state, "api_key_ctx", None)
            if ctx:
                owner_id = ctx["owner_id"]
                key_id = ctx["key_id"]
        except Exception:
            pass
        await log_request(request, response.status_code, started, owner_id, key_id)
    return response

# ---------- Maintenance check ----------
@app.middleware("http")
async def maintenance_guard(request: Request, call_next):
    path = request.url.path
    # Lewatkan: health, admin, static, landing, login, register, docs, maintenance
    bypass = (
        path.startswith("/api/admin") or path == "/api/health"
        or path.startswith("/public") or path in ("/", "/login", "/register",
                                                   "/documentation", "/maintenance")
        or path.startswith("/api/auth")
    )
    if not bypass:
        try:
            row = await db.fetchrow(
                "SELECT value FROM system_settings WHERE key='maintenance'"
            )
            if row and row["value"].get("enabled"):
                if path.startswith("/api/"):
                    return JSONResponse(
                        status_code=503,
                        content={
                            "success": False,
                            "message": row["value"].get("message", "Maintenance"),
                            "error": {"code": "MAINTENANCE_MODE"},
                        },
                    )
                return RedirectResponse("/maintenance", status_code=302)
        except Exception:
            pass
    return await call_next(request)

# ---------- Routers ----------
app.include_router(auth_router)
app.include_router(key_router)
app.include_router(magic_router)
app.include_router(analytics_router)
app.include_router(admin_router)

# ---------- Public API info ----------
@app.get("/api")
async def api_info():
    return {
        "success": True,
        "message": "AYAKA API is running",
        "data": {
            "name": "AYAKA API",
            "version": "1.0.0",
            "powered_by": "AYAKA Sync",
            "owner": "OLPI STORE",
            "documentation": f"{BASE_URL}/documentation",
        },
    }

# ---------- Visitor tracking (dipanggil dari frontend) ----------
@app.post("/api/track")
async def track_visitor(request: Request):
    from services.security import hash_ip
    ip = request.client.host if request.client else "0.0.0.0"
    vhash = hash_ip(ip + request.headers.get("user-agent", ""))
    try:
        await db.execute(
            "INSERT INTO visitor_analytics (visitor_hash, path) VALUES ($1,$2)",
            vhash, request.url.path,
        )
    except Exception:
        pass
    return {"success": True}

# ---------- Static files (opsional untuk local dev) ----------
# Di Vercel, static dilayani dari folder public/ secara otomatis.