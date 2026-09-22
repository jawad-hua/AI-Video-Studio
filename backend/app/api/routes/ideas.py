from fastapi import APIRouter

from app.models.ideas import IdeasRequest, IdeasResponse
from app.services.idea_service import create_ideas

router = APIRouter()


@router.post("/ideas", response_model=IdeasResponse)
def ideas(req: IdeasRequest) -> IdeasResponse:
    return IdeasResponse(ideas=create_ideas(req.niche, req.language))
