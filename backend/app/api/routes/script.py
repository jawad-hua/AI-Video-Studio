import logging

from fastapi import APIRouter

from app.config import JOBS_DIR
from app.models.schemas import ScriptRequest, VideoPlan
from app.services.script_service import create_script

router = APIRouter()
log = logging.getLogger(__name__)


@router.post("/script/generate", response_model=VideoPlan)
def generate_script(req: ScriptRequest) -> VideoPlan:
    plan = create_script(req)
    # Aage ke phases (Pexels, voice...) ko test karne ke liye last plan save hota hai
    try:
        JOBS_DIR.mkdir(parents=True, exist_ok=True)
        (JOBS_DIR / "last_plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    except OSError:
        log.exception("Could not save last_plan.json")
    return plan
