from fastapi import APIRouter

from app.api.routes.media import _load_last_plan
from app.models.voice import VoiceRequest, VoiceResult
from app.services.voice_service import generate_voice

router = APIRouter()


@router.post("/voice/generate", response_model=VoiceResult)
def voice_generate(req: VoiceRequest) -> VoiceResult:
    plan = req.plan or _load_last_plan()
    return generate_voice(plan, req.job_id, req.voice, req.max_total)
