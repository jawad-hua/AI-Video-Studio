from typing import Literal

from pydantic import BaseModel, Field


class IdeasRequest(BaseModel):
    niche: str | None = Field(default=None, max_length=60)  # e.g. "fitness", "AI tools"
    language: Literal["en", "ur"] = "en"


class IdeasResponse(BaseModel):
    ideas: list[str]
