from pydantic import BaseModel

from app.models.jobs import JobStatus
from app.models.schemas import VideoStyle


class ProjectItem(BaseModel):
    job_id: str
    status: JobStatus
    title: str
    topic: str
    style: VideoStyle
    duration: float | None = None
    elapsed_seconds: float | None = None
    created_at: str
    error: str | None = None
    thumbnail_url: str | None = None  # sirf completed videos ke liye
    video_url: str | None = None
    download_url: str | None = None
