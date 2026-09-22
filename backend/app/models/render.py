from typing import Literal

from pydantic import BaseModel, Field


class RenderRequest(BaseModel):
    job_id: str = Field(default="test", pattern=r"^[A-Za-z0-9_-]{1,64}$")
    quality: Literal["720p", "1080p"] | None = None  # None = .env (RENDER_WIDTH/RENDER_HEIGHT)
    music: bool = True         # assets/music mein track ho to hi lagta hai
    transitions: bool = True   # False = seedhe cuts (tez aur kam RAM)
    style: Literal["cinematic", "modern-tech", "documentary", "minimal"] = "modern-tech"
    sound_effects: bool = True


class RenderResult(BaseModel):
    job_id: str
    file: str            # backend/ ke relative path, e.g. generated/videos/test.mp4
    duration: float      # final video ki asli length (sec), hamesha <= 60
    width: int
    height: int
    size_mb: float
    transitions: bool    # asal mein transitions lage ya nahi (fallback hua to False)
    transition_names: list[str] = Field(default_factory=list)  # kaunsi transitions lagi (scene 2 se)
    sound_effects: bool = False  # whoosh sounds lage ya nahi
    music: str | None    # kaunsa music track use hua
