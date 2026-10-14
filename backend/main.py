"""FastAPI application assembly."""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from core.database import init_db
from routes import action_advice, api, geocode, tong_the


@asynccontextmanager
async def lifespan(_app: FastAPI):
    del _app
    init_db()
    polling_task = None
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        from core.notifications import polling_loop
        from core.scheduler import start_scheduler, stop_scheduler

        start_scheduler()
        polling_task = asyncio.create_task(polling_loop(), name="telegram-polling")
    try:
        yield
    finally:
        if polling_task is not None:
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
            stop_scheduler()


IS_PRODUCTION = os.getenv("APP_ENV", "").lower() == "production"
app = FastAPI(
    title="Huyền Học AI Pro",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
        ).split(",")
        if origin.strip()
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Chặn bot scan path nhạy cảm ──
_SCANNER_BLOCKLIST = (
    ".env", ".git", ".htaccess", ".htpasswd", ".ssh",
    "wp-admin", "wp-login", "wp-config", "wp-content",
    "phpmyadmin", "pma", "mysql", "admin.php", "setup.php",
    ".sql", ".bak", ".old", ".orig", ".swp",
    "/vendor/", "/node_modules/", "/.idea/", "/.vscode/",
    "config.php", "xmlrpc.php", "cgi-bin",
    "shell", "eval", "backup", "dump",
)


@app.middleware("http")
async def block_scanner_paths(request: Request, call_next):
    path = request.url.path.lower()
    # Bỏ qua static + api + docs thật
    if path.startswith(("/static/", "/api/", "/docs", "/openapi")):
        return await call_next(request)
    if any(b in path for b in _SCANNER_BLOCKLIST):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    return await call_next(request)


app.include_router(api.router)
app.include_router(geocode.router)
app.include_router(action_advice.router)
app.include_router(tong_the.router)

# ─── Static assets & PWA root files ───────────────────────────
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR / "static"),
    name="static",
)

@app.get("/manifest.json", include_in_schema=False)
def _manifest():
    return FileResponse(
        FRONTEND_DIR / "manifest.json",
        media_type="application/manifest+json",
    )

@app.get("/sw.js", include_in_schema=False)
def _sw():
    return FileResponse(
        FRONTEND_DIR / "static" / "js" / "sw.js",
        media_type="application/javascript",
    )

@app.get("/icon.svg", include_in_schema=False)
def _icon():
    return FileResponse(
        FRONTEND_DIR / "static" / "icons" / "icon.svg",
        media_type="image/svg+xml",
    )
