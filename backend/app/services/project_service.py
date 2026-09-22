"""Projects = purane jobs ki list (generated/jobs/*.json). Delete = us job ki saari files hatao."""
import re
import shutil

from app.config import AUDIO_DIR, JOBS_DIR, MEDIA_DIR, SUBTITLES_DIR, VIDEOS_DIR
from app.models.jobs import Job
from app.models.projects import ProjectItem
from app.services import job_service
from app.utils.errors import AppError

MAX_ITEMS = 50
_JOB_FILE = re.compile(r"^[0-9a-f]{12}\.json$")


def _item(job: Job) -> ProjectItem:
    done = job.status == "completed" and job.result is not None
    base = f"/api/video/{job.job_id}"
    return ProjectItem(
        job_id=job.job_id, status=job.status, title=job.title or job.request.topic,
        topic=job.request.topic, style=job.request.style,
        duration=job.result.duration if done else None,
        elapsed_seconds=job.elapsed_seconds if done else None,
        created_at=job.created_at, error=job.error,
        thumbnail_url=f"{base}/thumb/1" if done else None,
        video_url=f"{base}/file" if done else None,
        download_url=f"{base}/download" if done else None,
    )


KEEP_PROJECTS = 30  # is se purane (completed/failed) khud delete ho jate hain


def _all_jobs() -> list[Job]:
    jobs: list[Job] = []
    if JOBS_DIR.exists():
        for p in JOBS_DIR.glob("*.json"):
            if _JOB_FILE.match(p.name):
                try:
                    jobs.append(job_service.load_job(p.stem))
                except AppError:
                    continue  # kharab file poori list na rok de
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    return jobs


def list_projects() -> list[ProjectItem]:
    return [_item(j) for j in _all_jobs()[:MAX_ITEMS]]


def prune_old_projects(keep: int = KEEP_PROJECTS) -> int:
    """Disk bharne se bachao: sirf naye `keep` finished videos rakho. Delete hue jobs ki ginti return."""
    finished = [j for j in _all_jobs() if j.status in ("completed", "failed")]
    for old in finished[keep:]:
        delete_project(old.job_id)
    return max(0, len(finished) - keep)


def delete_project(job_id: str) -> None:
    job = job_service.load_job(job_id)  # galat id par 404
    if job.status not in ("completed", "failed"):
        raise AppError("This video is still being made. Wait until it finishes.", 409)
    for d in (MEDIA_DIR, AUDIO_DIR, SUBTITLES_DIR):
        shutil.rmtree(d / job.job_id, ignore_errors=True)
    shutil.rmtree(VIDEOS_DIR / f"{job.job_id}_work", ignore_errors=True)
    for f in (VIDEOS_DIR / f"{job.job_id}.mp4", JOBS_DIR / f"{job.job_id}_plan.json", JOBS_DIR / f"{job.job_id}.json"):
        f.unlink(missing_ok=True)
