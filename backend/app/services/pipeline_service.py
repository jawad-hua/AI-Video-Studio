"""Poori pipeline (script -> media -> voice -> subtitles -> render) ek background worker mein.

Ek waqt mein sirf ek job chalta hai (kam RAM wale laptop ke liye). Baaki queue mein intezar karte hain.
"""
import logging
import queue
import shutil
import threading
import time
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait
from typing import Callable

from app.config import AUDIO_DIR, JOBS_DIR, MEDIA_DIR, settings
from app.models.media import MediaResult
from app.models.schemas import ScriptRequest
from app.services import job_service, project_service
from app.services.pexels_service import fetch_media_for_plan
from app.services.render_service import render_video
from app.services.script_service import create_script
from app.services.subtitle_service import generate_subtitles
from app.services.video_service import FFmpegError, run_ffmpeg
from app.services.voice_service import generate_voice
from app.utils.errors import AppError

log = logging.getLogger(__name__)

MAX_PENDING = 3  # queue mein is se zyada jobs nahi
_queue: "queue.Queue[str]" = queue.Queue()
_thread: threading.Thread | None = None


# ---------------------------------------------------------------- worker
def start_worker() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=_loop, name="video-worker", daemon=True)
    _thread.start()
    log.info("Video worker started")


def _loop() -> None:
    while True:
        job_id = _queue.get()
        try:
            run_pipeline(job_id)
        except Exception:  # run_pipeline khud sab pakadta hai, ye sirf safety hai
            log.exception("Worker crashed on job %s", job_id)
        finally:
            _queue.task_done()


def preflight() -> None:
    """Job banane se PEHLE zaroori cheezein check karo: user ko foran saaf message mile, 2 minute baad nahi."""
    if not shutil.which("ffmpeg"):
        raise AppError("FFmpeg is not installed. Install it, then restart the backend.", 503)
    if not settings.groq_api_key.strip():
        raise AppError("Groq API key is missing. Add GROQ_API_KEY to backend/.env and restart the backend.", 503)
    if not settings.pexels_api_key.strip():
        raise AppError("Pexels API key is missing. Add PEXELS_API_KEY to backend/.env and restart the backend.", 503)


def enqueue(job_id: str) -> None:
    if _queue.qsize() >= MAX_PENDING:
        raise AppError("Too many videos are being made right now. Please wait a few minutes and try again.", 429)
    _queue.put(job_id)


# -------------------------------------------------------------- progress
def _reporter(job_id: str, lo: int, hi: int) -> Callable[[float], None]:
    """0..1 ka fraction lo%..hi% mein badal kar job file mein likhta hai (peechhe nahi jata, bar bar nahi likhta)."""
    state = {"pct": lo, "t": 0.0}

    def report(frac: float) -> None:
        pct = lo + int((hi - lo) * min(1.0, max(0.0, frac)))
        now = time.monotonic()
        if pct > state["pct"] and (now - state["t"] > 0.7 or pct - state["pct"] >= 3):
            state["pct"], state["t"] = pct, now
            try:
                job_service.update_job(job_id, progress=pct)
            except Exception:  # progress ki wajah se job fail nahi hona chahiye
                log.warning("Could not save progress for %s", job_id)

    return report


# -------------------------------------------------------------- pipeline
def _thumbnails(job_id: str) -> None:
    """Har scene ka chhota JPG thumbnail (timeline ke liye). Fail ho to koi masla nahi."""
    try:
        media = MediaResult.model_validate_json((MEDIA_DIR / job_id / "media.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    base = MEDIA_DIR.parent.parent
    for m in media.items:
        src, out = base / m.file, MEDIA_DIR / job_id / f"thumb_{m.scene_number:02d}.jpg"
        seek = ["-ss", "0.3"] if m.type == "video" else []
        try:
            run_ffmpeg([*seek, "-i", str(src), "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "4", str(out)], timeout=30)
        except FFmpegError:
            log.warning("Thumbnail failed for scene %s", m.scene_number)


def cleanup_raw(job_id: str) -> None:
    """Video ban chuki hai: bade raw clips/audio hata do (100 MB+ bachte hain). Thumbnails aur JSON files rehti hain."""
    for folder, pattern in ((MEDIA_DIR / job_id, "scene_*"), (AUDIO_DIR / job_id, "scene_*")):
        for f in folder.glob(pattern):
            f.unlink(missing_ok=True)


def run_pipeline(job_id: str) -> None:
    upd = job_service.update_job
    try:
        req = job_service.load_job(job_id).request
        voice = req.voice or settings.tts_voice
        language = "ur" if voice.lower().startswith("ur-") else "en"

        t_start = time.monotonic()
        timings: dict[str, float] = {}
        mark = t_start

        def lap(name: str) -> None:
            nonlocal mark
            now = time.monotonic()
            timings[name] = round(now - mark, 1)
            mark = now

        upd(job_id, status="analyzing", progress=5, started_at=job_service._now())
        upd(job_id, status="scripting", progress=10)
        plan = create_script(ScriptRequest(topic=req.topic, duration=req.duration, style=req.style, language=language))
        plan_json = plan.model_dump_json(indent=2)
        (JOBS_DIR / f"{job_id}_plan.json").write_text(plan_json, encoding="utf-8")
        (JOBS_DIR / "last_plan.json").write_text(plan_json, encoding="utf-8")  # render transitions yahin se padhta hai
        upd(job_id, title=plan.title)
        lap("script")

        # Media download aur voice ek dusre par depend nahi karte: dono ek saath (waqt bachta hai)
        upd(job_id, status="fetching_media", progress=25)
        fracs = [0.0, 0.0]
        report = _reporter(job_id, 25, 68)

        def part(i: int) -> Callable[[float], None]:
            def cb(x: float) -> None:
                fracs[i] = x
                report(sum(fracs) / 2)
            return cb

        pool = ThreadPoolExecutor(max_workers=2)
        try:
            f_media = pool.submit(fetch_media_for_plan, plan, job_id, on_progress=part(0))
            f_voice = pool.submit(generate_voice, plan, job_id, voice, req.duration, on_progress=part(1))
            finished, _ = wait([f_media, f_voice], return_when=FIRST_EXCEPTION)
            for f in finished:
                f.result()  # ek bhi fail hua to yahin error upar jayega
            wait([f_media, f_voice])
            f_media.result()
            f_voice.result()
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        lap("media_voice")

        upd(job_id, status="creating_subtitles", progress=68)
        generate_subtitles(job_id, req.style, req.watermark)
        lap("subtitles")

        upd(job_id, status="rendering", progress=75)
        result = render_video(job_id, quality=req.resolution, music=req.background_music,
                              on_progress=_reporter(job_id, 75, 99), speed=req.speed,
                              style=req.style, sfx=req.sound_effects)
        lap("render")
        _thumbnails(job_id)
        cleanup_raw(job_id)
        lap("cleanup")

        total = round(time.monotonic() - t_start, 1)
        timings["total"] = total
        upd(job_id, status="completed", progress=100, result=result, elapsed_seconds=total, timings=timings)
        job_service.record_completion(total)
        log.info("Job %s completed (%.1fs video) timings=%s", job_id, result.duration, timings)

        try:
            removed = project_service.prune_old_projects()
            if removed:
                log.info("Pruned %s old projects", removed)
        except Exception:
            log.exception("Pruning old projects failed")

    except AppError as e:
        log.warning("Job %s failed: %s", job_id, e.message)
        _fail(job_id, e.message)
    except Exception:
        log.exception("Job %s crashed", job_id)
        _fail(job_id, "Something went wrong while creating the video. Please try again.")


def _fail(job_id: str, message: str) -> None:
    try:
        job_service.update_job(job_id, status="failed", error=message)
    except Exception:
        log.exception("Could not save failed state for %s", job_id)
