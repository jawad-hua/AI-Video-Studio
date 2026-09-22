from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.render import RenderResult
from app.models.schemas import VideoStyle

JobStatus = Literal[
    "queued", "analyzing", "scripting", "fetching_media", "generating_voice",
    "creating_subtitles", "rendering", "completed", "failed",
]

STATUS_LABELS: dict[str, str] = {
    "queued": "Waiting in queue",
    "analyzing": "Analyzing topic",
    "scripting": "Generating script",
    "fetching_media": "Collecting media and voice",
    "generating_voice": "Generating voice",
    "creating_subtitles": "Creating subtitles",
    "rendering": "Rendering video",
    "completed": "Video ready",
    "failed": "Failed",
}


# Frontend ki request se same field names
class GenerateVideoRequest(BaseModel):
    topic: str = Field(min_length=5, max_length=300)
    duration: Literal[30, 45, 60] = 60
    aspect_ratio: Literal["9:16"] = "9:16"
    style: VideoStyle = "modern-tech"
    voice: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{5,60}$")  # None = .env ka TTS_VOICE
    resolution: Literal["720p", "1080p"] = "720p"
    background_music: bool = True
    sound_effects: bool = True  # transition par halki whoosh awaaz
    speed: Literal["fast", "balanced"] = "fast"  # fast = tez render, balanced = thodi behtar quality
    watermark: str | None = Field(default=None, max_length=40)  # brand handle, e.g. "@mychannel"

    @field_validator("watermark", mode="before")
    @classmethod
    def _clean_watermark(cls, v):
        if v is None:
            return None
        v = "".join(ch for ch in str(v) if ch not in "{}\\\r\n").strip()[:30]
        return v or None


class CreateJobResponse(BaseModel):
    job_id: str


class Job(BaseModel):
    job_id: str
    status: JobStatus = "queued"
    progress: int = 0
    error: str | None = None
    request: GenerateVideoRequest
    title: str | None = None
    result: RenderResult | None = None
    started_at: str | None = None
    elapsed_seconds: float | None = None  # pipeline ka total time (queue ke bina)
    timings: dict[str, float] = Field(default_factory=dict)  # har stage ka time (sec)
    created_at: str
    updated_at: str


class StatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int
    current_step: str
    error: str | None = None
    elapsed_seconds: float = 0
    typical_seconds: int | None = None  # pichhli videos ka average time (aap ke computer par)


class SceneInfo(BaseModel):
    number: int
    start: float
    duration: float
    narration: str
    subtitle: str
    media_type: Literal["video", "image"]
    media_source: Literal["pexels", "fallback"]
    thumbnail_url: str


class VideoInfo(BaseModel):
    job_id: str
    title: str
    topic: str
    style: VideoStyle
    duration: float
    width: int
    height: int
    size_mb: float
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    elapsed_seconds: float | None = None
    video_url: str
    download_url: str
    scenes: list[SceneInfo]
