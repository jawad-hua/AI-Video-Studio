from typing import Literal

from pydantic import BaseModel, Field

from app.models.schemas import VideoPlan


class MediaFetchRequest(BaseModel):
    # job_id folder ka naam banta hai, isliye sirf safe characters allowed
    job_id: str = Field(default="test", pattern=r"^[A-Za-z0-9_-]{1,64}$")
    plan: VideoPlan | None = None  # None ho to generated/jobs/last_plan.json use hoga


class MediaItem(BaseModel):
    scene_number: int
    type: Literal["video", "image"]
    source: Literal["pexels", "fallback"]
    file: str  # backend/ folder ke relative path, e.g. generated/media/test/scene_01.mp4
    query: str | None = None
    pexels_id: int | None = None
    pexels_url: str | None = None
    credit: str | None = None
    width: int | None = None
    height: int | None = None
    duration: float | None = None  # sirf video ke liye (seconds)


class MediaResult(BaseModel):
    job_id: str
    videos: int
    images: int
    fallbacks: int
    items: list[MediaItem]
