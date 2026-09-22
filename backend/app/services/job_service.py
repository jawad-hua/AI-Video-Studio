"""Jobs ka state: har job ek chhoti JSON file (generated/jobs/{job_id}.json). Koi database nahi."""
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone

from app.config import AUDIO_DIR, JOBS_DIR, MEDIA_DIR
from app.models.jobs import (
    STATUS_LABELS, GenerateVideoRequest, Job, SceneInfo, StatusResponse, VideoInfo,
)
from app.models.media import MediaResult
from app.models.schemas import VideoPlan
from app.models.voice import VoiceResult
from app.utils.errors import AppError

log = logging.getLogger(__name__)

_JOB_ID = re.compile(r"^[0-9a-f]{12}$")
# RLock: padhna aur likhna dono isi lock ke andar, taake status polling aur progress update ek saath file na chhuen.
# (Windows par jab ek thread file khole ho, doosre ka os.replace/read "Permission denied" deta hai.)
_lock = threading.RLock()


def _retry_io(fn, attempts: int = 6, delay: float = 0.05):
    """Antivirus/indexer jaise bahar ke programs bhi file thodi der pakad sakte hain: chhota sa retry."""
    for i in range(attempts):
        try:
            return fn()
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(delay)


def _path(job_id: str):
    if not _JOB_ID.match(job_id):  # path traversal se bachao
        raise AppError("Video not found.", 404)
    return JOBS_DIR / f"{job_id}.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save(job: Job) -> None:
    path = _path(job.job_id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(job.model_dump_json(indent=2), encoding="utf-8")
    _retry_io(lambda: os.replace(tmp, path))  # atomic: padhne wala adhoori file kabhi nahi dekhta


def create_job(req: GenerateVideoRequest) -> Job:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    now = _now()
    job = Job(job_id=uuid.uuid4().hex[:12], request=req, created_at=now, updated_at=now)
    with _lock:
        _save(job)
    return job


def load_job(job_id: str) -> Job:
    path = _path(job_id)
    with _lock:
        try:
            text = _retry_io(lambda: path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise AppError("Video not found.", 404)
    try:
        return Job.model_validate_json(text)
    except ValueError:
        log.exception("Job file invalid: %s", job_id)
        raise AppError("Video data is corrupted.", 500)


def update_job(job_id: str, **fields) -> Job:
    with _lock:
        job = load_job(job_id).model_copy(update={**fields, "updated_at": _now()})
        _save(job)
    return job


def mark_stale_jobs_failed() -> None:
    """Server band hone se adhoore reh gaye jobs ko 'failed' karo (warna frontend hamesha poll karta rahega)."""
    if not JOBS_DIR.exists():
        return
    for p in JOBS_DIR.glob("*.json"):
        if not _JOB_ID.match(p.stem):
            continue
        try:
            job = load_job(p.stem)
        except AppError:
            continue
        if job.status not in ("completed", "failed"):
            update_job(job.job_id, status="failed", error="The server was restarted. Please generate the video again.")
            log.warning("Marked stale job %s as failed", job.job_id)


_history: list[float] = []  # pichhle 5 completed jobs ka total time (sec)


def record_completion(elapsed: float) -> None:
    with _lock:
        _history.append(elapsed)
        del _history[:-5]


def typical_seconds() -> int | None:
    with _lock:
        return round(sum(_history) / len(_history)) if _history else None


def load_history() -> None:
    """Server start par purani completed jobs se 'aam taur par kitna time lagta hai' seekho."""
    if not JOBS_DIR.exists():
        return
    done = []
    for p in JOBS_DIR.glob("*.json"):
        if _JOB_ID.match(p.stem):
            try:
                job = load_job(p.stem)
            except AppError:
                continue
            if job.status == "completed" and job.elapsed_seconds:
                done.append(job)
    done.sort(key=lambda j: j.created_at)
    with _lock:
        _history[:] = [j.elapsed_seconds for j in done[-5:]]


def _elapsed(job: Job) -> float:
    if not job.started_at:
        return 0.0
    start = datetime.fromisoformat(job.started_at)
    running = job.status not in ("completed", "failed")
    end = datetime.now(timezone.utc) if running else datetime.fromisoformat(job.updated_at)
    return max(0.0, (end - start).total_seconds())


def to_status(job: Job) -> StatusResponse:
    return StatusResponse(
        job_id=job.job_id, status=job.status, progress=job.progress,
        current_step=STATUS_LABELS[job.status], error=job.error,
        elapsed_seconds=round(_elapsed(job), 1), typical_seconds=typical_seconds(),
    )


def build_video_info(job: Job) -> VideoInfo:
    """Poori ho chuki video ki details: title, scenes (thumbnail, narration, media source)."""
    if job.status != "completed" or not job.result:
        raise AppError("The video is not ready yet.", 409)
    try:
        plan = VideoPlan.model_validate_json((JOBS_DIR / f"{job.job_id}_plan.json").read_text(encoding="utf-8"))
        voice = VoiceResult.model_validate_json((AUDIO_DIR / job.job_id / "voice.json").read_text(encoding="utf-8"))
        media = MediaResult.model_validate_json((MEDIA_DIR / job.job_id / "media.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log.exception("Could not load data for video info %s", job.job_id)
        raise AppError("Video data is missing. Please generate the video again.", 500)

    media_by = {m.scene_number: m for m in media.items}
    plan_by = {s.scene_number: s for s in plan.scenes}
    scenes = []
    for v in voice.items:
        m, s = media_by[v.scene_number], plan_by.get(v.scene_number)
        scenes.append(SceneInfo(
            number=v.scene_number, start=v.start, duration=v.duration,
            narration=s.narration if s else v.text, subtitle=s.subtitle if s else "",
            media_type=m.type, media_source=m.source,
            thumbnail_url=f"/api/video/{job.job_id}/thumb/{v.scene_number}",
        ))
    r = job.result
    return VideoInfo(
        job_id=job.job_id, title=job.title or plan.title, topic=job.request.topic, style=job.request.style,
        duration=r.duration, width=r.width, height=r.height, size_mb=r.size_mb,
        caption=plan.caption, hashtags=plan.hashtags, elapsed_seconds=job.elapsed_seconds,
        video_url=f"/api/video/{job.job_id}/file", download_url=f"/api/video/{job.job_id}/download",
        scenes=scenes,
    )
