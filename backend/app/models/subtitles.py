from pydantic import BaseModel, Field

from app.models.schemas import VideoStyle


class SubtitleRequest(BaseModel):
    job_id: str = Field(default="test", pattern=r"^[A-Za-z0-9_-]{1,64}$")
    style: VideoStyle = "modern-tech"


class CueWord(BaseModel):
    text: str
    start: float  # video timeline par (sec)
    end: float


class Cue(BaseModel):
    scene_number: int
    start: float
    end: float
    text: str
    words: list[CueWord] = Field(default_factory=list)  # lafz-ba-lafz timing (highlight ke liye)


class SubtitleResult(BaseModel):
    job_id: str
    style: VideoStyle
    file: str  # backend/ ke relative path, e.g. generated/subtitles/test/subtitles.ass
    cue_count: int
    cues: list[Cue]
