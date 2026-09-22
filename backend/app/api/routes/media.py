import logging

from fastapi import APIRouter

from app.config import JOBS_DIR
from app.models.media import MediaFetchRequest, MediaResult
from app.models.schemas import VideoPlan
from app.services.pexels_service import fetch_media_for_plan
from app.utils.errors import AppError

router = APIRouter()
log = logging.getLogger(__name__)


def _load_last_plan() -> VideoPlan:
    path = JOBS_DIR / "last_plan.json"
    if not path.exists():
        raise AppError("No script found yet. Run POST /api/script/generate first.", 404)
    try:
        return VideoPlan.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError:
        log.exception("last_plan.json is invalid")
        raise AppError("Saved script is invalid. Generate a new script first.", 422)


@router.post("/media/fetch", response_model=MediaResult)
def fetch_media(req: MediaFetchRequest) -> MediaResult:
    plan = req.plan or _load_last_plan()
    return fetch_media_for_plan(plan, req.job_id)
