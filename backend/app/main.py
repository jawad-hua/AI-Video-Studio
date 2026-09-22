import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, ideas, media, projects, render, script, subtitles, video, voice
from app.config import ensure_dirs
from app.services.job_service import load_history, mark_stale_jobs_failed
from app.services.project_service import prune_old_projects
from app.services.pipeline_service import start_worker
from app.utils.errors import AppError
from app.utils.logging import setup_logging

setup_logging()
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    mark_stale_jobs_failed()  # pichhli baar adhoore reh gaye jobs
    load_history()            # 'aam taur par kitna time lagta hai' (ETA ke liye)
    try:
        prune_old_projects()  # sirf naye 30 videos rakho (disk)
    except Exception:
        log.exception("Startup prune failed")
    start_worker()            # background worker: ek waqt mein ek video
    log.info("AI Video Studio API started")
    yield


app = FastAPI(title="AI Video Studio API", version="0.10.0", lifespan=lifespan)

# Sirf local frontend ko allow karo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# User-friendly errors: message frontend ko, technical detail sirf log mein
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})


app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(script.router, prefix="/api", tags=["script"])
app.include_router(media.router, prefix="/api", tags=["media"])
app.include_router(voice.router, prefix="/api", tags=["voice"])
app.include_router(subtitles.router, prefix="/api", tags=["subtitles"])
app.include_router(render.router, prefix="/api", tags=["render"])
app.include_router(video.router, prefix="/api", tags=["video"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(ideas.router, prefix="/api", tags=["ideas"])
