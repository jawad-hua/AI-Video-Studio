from fastapi import APIRouter

from app.models.projects import ProjectItem
from app.services import project_service

router = APIRouter()


@router.get("/projects", response_model=list[ProjectItem])
def projects() -> list[ProjectItem]:
    return project_service.list_projects()


@router.delete("/projects/{job_id}", status_code=204)
def remove(job_id: str) -> None:
    project_service.delete_project(job_id)
