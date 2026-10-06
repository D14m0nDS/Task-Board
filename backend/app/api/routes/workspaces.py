import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, WorkspaceMembership, WorkspaceOwnership
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberCreate,
    WorkspaceMemberRead,
    WorkspaceMemberUpdate,
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


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberRead,
    status_code=status.HTTP_201_CREATED,
)
def add_workspace_member(
    db: DbSession, membership: WorkspaceOwnership, payload: WorkspaceMemberCreate
) -> WorkspaceMember:
    try:
        return workspace_service.add_member(db, membership.workspace, payload.email, payload.role)
    except workspace_service.AlreadyAMemberError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already a member of the workspace",
        ) from None
    except workspace_service.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None


@router.patch("/{workspace_id}/members/{user_id}", response_model=WorkspaceMemberRead)
def change_workspace_member_role(
    db: DbSession,
    membership: WorkspaceOwnership,
    user_id: uuid.UUID,
    payload: WorkspaceMemberUpdate,
) -> WorkspaceMember:
    try:
        return workspace_service.change_member_role(
            db, membership.workspace, user_id, payload.role
        )
    except workspace_service.NotAMemberError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of the workspace",
        ) from None
    except workspace_service.LastOwnerError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot change the role of the last owner",
        ) from None


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_workspace_member(
    db: DbSession, membership: WorkspaceOwnership, user_id: uuid.UUID
) -> None:
    try:
        workspace_service.remove_member(db, membership.workspace, user_id)
    except workspace_service.NotAMemberError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of the workspace",
        ) from None
    except workspace_service.LastOwnerError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot remove the last owner",
        ) from None