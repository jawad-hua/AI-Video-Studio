from typing import Literal

from pydantic import BaseModel, Field

from app.models.schemas import VideoPlan


class VoiceRequest(BaseModel):
    job_id: str = Field(default="test", pattern=r"^[A-Za-z0-9_-]{1,64}$")
    voice: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{5,60}$")  # None = .env ka TTS_VOICE
    max_total: Literal[30, 45, 60] = 60
    plan: VideoPlan | None = None  # None ho to generated/jobs/last_plan.json use hoga


class WordTiming(BaseModel):
    text: str
    start: float  # scene ki audio ke shuru se (sec)
    end: float


class VoiceItem(BaseModel):
    scene_number: int
    file: str              # backend/ ke relative path, e.g. generated/audio/test/scene_01.mp3
    text: str
    audio_duration: float  # narration ki asli length (sec)
    duration: float        # scene ki final length = narration + chhota gap
    start: float           # video timeline par scene kahan se shuru hota hai
    words: list[WordTiming] = Field(default_factory=list)  # asli word timings (TTS ne diye ho to), warna khali


class VoiceResult(BaseModel):
    job_id: str
    voice: str
    speed: float           # 1.0 = normal; zyada ho to fit karne ke liye audio tez kiya gaya
    total_duration: float
    items: list[VoiceItem]
