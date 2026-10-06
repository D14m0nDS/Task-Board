from fastapi import APIRouter, HTTPException, status

from app.api.deps import (
    DbSession,
    ProjectAccess,
    ProjectOwnership,
    WorkspaceMembership,
    WorkspaceOwnership,
)
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services import project_service

router = APIRouter(prefix="/workspaces/{workspace_id}/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate, db: DbSession, ownership: WorkspaceOwnership
) -> Project:
    try:
        return project_service.create_project(db, ownership.workspace, payload)
    except project_service.ProjectKeyTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A project with this key already exists in the workspace",
        ) from None


@router.get("", response_model=list[ProjectRead])
def list_projects(db: DbSession, membership: WorkspaceMembership) -> list[Project]:
    return project_service.list_projects(db, membership.workspace_id)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project: ProjectAccess) -> Project:
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(db: DbSession, project: ProjectOwnership, payload: ProjectUpdate) -> Project:
    return project_service.update_project(db, project, payload)
