from fastapi import APIRouter

from app.models.subtitles import SubtitleRequest, SubtitleResult
from app.services.subtitle_service import generate_subtitles

router = APIRouter()


@router.post("/subtitles/generate", response_model=SubtitleResult)
def subtitles_generate(req: SubtitleRequest) -> SubtitleResult:
    return generate_subtitles(req.job_id, req.style)
