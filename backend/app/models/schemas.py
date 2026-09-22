from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

VideoStyle = Literal["cinematic", "modern-tech", "documentary", "minimal"]
Transition = Literal["fade", "slide", "zoom"]


class ScriptRequest(BaseModel):
    topic: str = Field(min_length=5, max_length=300)
    duration: Literal[30, 45, 60] = 60
    style: VideoStyle = "modern-tech"
    language: Literal["en", "ur"] = "en"


class Scene(BaseModel):
    scene_number: int = 0
    duration: float = Field(default=6, gt=0)
    narration: str = Field(min_length=3)
    visual_description: str = ""
    search_keywords: list[str] = Field(min_length=1)
    subtitle: str = ""
    transition: Transition = "fade"

    # LLM kabhi kabhi "keyword1, keyword2" string bhej deta hai
    @field_validator("search_keywords", mode="before")
    @classmethod
    def _keywords_to_list(cls, v):
        if isinstance(v, str):
            v = [p.strip() for p in v.split(",")]
        if isinstance(v, list):
            v = [str(k).strip() for k in v if str(k).strip()][:5]
        return v

    # Unknown transition aaye to crash nahi, "fade" use karo
    @field_validator("transition", mode="before")
    @classmethod
    def _safe_transition(cls, v):
        return v if v in ("fade", "slide", "zoom") else "fade"

    @model_validator(mode="after")
    def _fill_subtitle(self):
        if not self.subtitle.strip():
            self.subtitle = self.narration.strip()[:60]
        return self


class VideoPlan(BaseModel):
    title: str = Field(min_length=3)
    caption: str = ""                                  # TikTok/Reels post ka caption
    hashtags: list[str] = Field(default_factory=list)  # e.g. ["#AI", "#Tech"]
    scenes: list[Scene] = Field(min_length=5, max_length=12)

    @field_validator("hashtags", mode="before")
    @classmethod
    def _clean_hashtags(cls, v):
        if isinstance(v, str):
            v = v.replace(",", " ").split()
        if not isinstance(v, list):
            return []
        tags = []
        for t in v:
            t = "".join(ch for ch in str(t).strip().lstrip("#") if ch.isalnum() or ch == "_")
            if t and f"#{t}" not in tags:
                tags.append(f"#{t}")
        return tags[:8]

    @computed_field
    @property
    def total_duration(self) -> float:
        return round(sum(s.duration for s in self.scenes), 1)
