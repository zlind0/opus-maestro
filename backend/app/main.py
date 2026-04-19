import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import engine, init_db
from app.routers import auth, audio, music, recommend, scan

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Classical Music Player API",
    version="0.1.0",
    description="AI-driven classical music streaming system",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(music.router)
app.include_router(audio.router)
app.include_router(recommend.router)
app.include_router(scan.router)


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health")
async def health_check():
    db_status = "connected"
    llm_status = "available"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    if not settings.openai_api_key:
        llm_status = "not_configured"

    status = "ok" if db_status == "connected" else "degraded"
    issues = []
    if db_status != "connected":
        issues.append("db_disconnected")
    if llm_status != "available":
        issues.append("llm_unavailable")

    response = {"status": status, "db": db_status, "llm": llm_status}
    if issues:
        response["issues"] = issues
    return response
