import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text
from app.database import engine

from app.database import init_db
from app.config import (
    BASE_DIR, STORAGE_DIR, STATIC_DIR, BGM_DIR, FFMPEG_PATH, FFPROBE_PATH
)
from app.routers import projects, clips, export

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("autoclip.main")

def generate_sample_bgm():
    """Generates a pleasant synthetic background music loop if no files exist."""
    sample_file = BGM_DIR / "lofi_chill.mp3"
    if not sample_file.exists() or sample_file.stat().st_size == 0:
        try:
            import subprocess
            # Generate a 10s gentle chord sweep using FFmpeg synthesizer with explicit -t 10
            cmd = [
                FFMPEG_PATH,
                "-y",
                "-f", "lavfi",
                "-i", "sine=frequency=220",
                "-t", "10",
                "-af", "volume=0.3,lowpass=f=800",
                "-c:a", "libmp3lame",
                str(sample_file)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            logger.info("Generated sample BGM track: %s", sample_file)
        except Exception as e:
            logger.debug("Could not generate synthetic BGM: %s", e)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("AutoClip AI initializing...")
    logger.info("Detected FFmpeg binary: %s", FFMPEG_PATH)
    logger.info("Detected FFprobe binary: %s", FFPROBE_PATH)
    init_db()
    generate_sample_bgm()
    yield
    # Shutdown
    logger.info("AutoClip AI shutting down.")

app = FastAPI(
    title="AutoClip AI – Long-to-Short Video Repurposing Platform",
    description="Intelligent Analysis + Explainable Scoring + Automatic Editing + Professional Output",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Mount Storage for streaming video/audio and thumbnails
app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")

# Include Routers
app.include_router(projects.router)
app.include_router(clips.router)
app.include_router(export.router)

# Mount Static Files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/health")
def health_check():
    """Readiness check used by container and load-balancer health probes."""
    database_ok = False
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        logger.exception("Database readiness check failed")

    ffmpeg_ok = Path(FFMPEG_PATH).exists() or shutil_which_exists(FFMPEG_PATH)
    healthy = database_ok and ffmpeg_ok
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "healthy" if healthy else "not_ready",
            "service": "AutoClip AI",
            "checks": {"database": database_ok, "ffmpeg": ffmpeg_ok},
        },
    )

def shutil_which_exists(name):
    import shutil
    return bool(shutil.which(name))

# Serve Frontend SPA
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str, request: Request):
    # Exclude API endpoints
    if full_path.startswith("api/") or full_path.startswith("storage/") or full_path.startswith("static/"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
        
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse(status_code=200, content={"message": "AutoClip AI API Active. Frontend index.html loading..."})
