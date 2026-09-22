from fastapi import APIRouter

from app.models.render import RenderRequest, RenderResult
from app.services.render_service import render_video

router = APIRouter()


@router.post("/render/generate", response_model=RenderResult)
def render_generate(req: RenderRequest) -> RenderResult:
    return render_video(req.job_id, req.quality, req.music, req.transitions, style=req.style, sfx=req.sound_effects)
