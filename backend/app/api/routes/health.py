import logging
import shutil
import subprocess

from fastapi import APIRouter

from app.config import settings

router = APIRouter()
log = logging.getLogger(__name__)


def _ffmpeg_info() -> dict:
    path = shutil.which("ffmpeg")
    if not path:
        return {"found": False, "version": None}
    try:
        out = subprocess.run(
            [path, "-version"], capture_output=True, text=True, timeout=5
        ).stdout
        version = out.splitlines()[0] if out else None
    except Exception:
        log.exception("ffmpeg version check failed")
        version = None
    return {"found": True, "version": version}


@router.get("/health")
def health() -> dict:
    ffmpeg = _ffmpeg_info()
    groq_ok = bool(settings.groq_api_key.strip())
    pexels_ok = bool(settings.pexels_api_key.strip())

    # User-friendly warnings (keys ki value kabhi return nahi hoti, sirf True/False)
    warnings = []
    if not ffmpeg["found"]:
        warnings.append("FFmpeg not found. Install it and restart the terminal.")
    if not groq_ok:
        warnings.append("GROQ_API_KEY is missing in backend/.env")
    if not pexels_ok:
        warnings.append("PEXELS_API_KEY is missing in backend/.env")

    return {
        "status": "ok",
        "app": "AI Video Studio API",
        "ffmpeg": ffmpeg,
        "config": {
            "groq_api_key_set": groq_ok,
            "pexels_api_key_set": pexels_ok,
            "groq_model": settings.groq_model,
            "tts_provider": settings.tts_provider,
            "render_size": f"{settings.render_width}x{settings.render_height}",
        },
        "warnings": warnings,
    }
