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
from app.schemas.label import LabelRead, LabelCreate
from app.models.label import Label
from app.services import project_service, label_service

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

@router.get("/{project_id}/labels", response_model=list[LabelRead])
def list_labels(db: DbSession, project: ProjectAccess) -> list[Label]:
    return label_service.list_labels(db, project.id)

@router.post("/{project_id}/labels", response_model=LabelRead, status_code=status.HTTP_201_CREATED)
def create_label(db: DbSession, project: ProjectAccess, payload: LabelCreate) -> Label:
    try:
        return label_service.create_label(db, project, payload)
    except label_service.LabelNameTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A label with this name already exists in the project",
        ) from None
