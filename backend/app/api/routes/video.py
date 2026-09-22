import re

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.config import MEDIA_DIR, VIDEOS_DIR
from app.models.jobs import CreateJobResponse, GenerateVideoRequest, StatusResponse, VideoInfo
from app.services import job_service
from app.services.pipeline_service import enqueue, preflight
from app.utils.errors import AppError

router = APIRouter()


@router.post("/video/generate", response_model=CreateJobResponse)
def generate(req: GenerateVideoRequest) -> CreateJobResponse:
    preflight()  # keys/FFmpeg na hon to job banane se pehle hi saaf error
    job = job_service.create_job(req)
    try:
        enqueue(job.job_id)
    except AppError:
        job_service.update_job(job.job_id, status="failed", error="Too many videos in progress.")
        raise
    return CreateJobResponse(job_id=job.job_id)


@router.get("/video/status/{job_id}", response_model=StatusResponse)
def status(job_id: str) -> StatusResponse:
    return job_service.to_status(job_service.load_job(job_id))


@router.get("/video/{job_id}", response_model=VideoInfo)
def info(job_id: str) -> VideoInfo:
    return job_service.build_video_info(job_service.load_job(job_id))


def _video_path(job_id: str):
    job = job_service.load_job(job_id)
    path = VIDEOS_DIR / f"{job.job_id}.mp4"
    if job.status != "completed" or not path.exists():
        raise AppError("The video is not ready yet.", 409)
    return job, path


@router.get("/video/{job_id}/file")
def file(job_id: str) -> FileResponse:
    _, path = _video_path(job_id)
    return FileResponse(path, media_type="video/mp4")  # Range support: player seeking chalti hai


@router.get("/video/{job_id}/download")
def download(job_id: str) -> FileResponse:
    job, path = _video_path(job_id)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", job.title or "video").strip("-")[:50] or "video"
    return FileResponse(path, media_type="video/mp4", filename=f"{slug}.mp4")


@router.get("/video/{job_id}/thumb/{scene_number}")
def thumb(job_id: str, scene_number: int) -> FileResponse:
    job = job_service.load_job(job_id)
    path = MEDIA_DIR / job.job_id / f"thumb_{scene_number:02d}.jpg"
    if not path.exists():
        raise AppError("Thumbnail not found.", 404)
    return FileResponse(path, media_type="image/jpeg")
