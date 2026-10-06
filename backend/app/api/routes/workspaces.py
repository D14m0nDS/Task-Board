from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession, WorkspaceMembership, WorkspaceOwnership
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberRead,
    WorkspaceRead,
    WorkspaceUpdate,
)
from app.services import workspace_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate, db: DbSession, current_user: CurrentUser
) -> Workspace:
    return workspace_service.create_workspace(db, current_user, payload)


@router.get("", response_model=list[WorkspaceRead])
def list_workspaces(db: DbSession, current_user: CurrentUser) -> list[Workspace]:
    return workspace_service.list_workspaces_for_user(db, current_user.id)


@router.get("/{workspace_id}", response_model=WorkspaceRead)
def get_workspace(membership: WorkspaceMembership) -> Workspace:
    return membership.workspace


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberRead])
def list_workspace_members(membership: WorkspaceMembership) -> list[WorkspaceMember]:
    return membership.workspace.members


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
def update_workspace(
    db: DbSession, membership: WorkspaceOwnership, payload: WorkspaceUpdate
) -> Workspace:
    return workspace_service.update_workspace(db, membership.workspace, payload)