import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


def get_membership(
    db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> WorkspaceMember | None:
    """The caller's membership row, or None if they are not a member.

    This is the only question the permission layer needs to ask: it answers
    both "may they see the workspace" and "what may they do in it".
    """
    return db.get(WorkspaceMember, {"workspace_id": workspace_id, "user_id": user_id})


def list_workspaces_for_user(db: Session, user_id: uuid.UUID) -> list[Workspace]:
    statement = (
        select(Workspace)
        .join(WorkspaceMember)
        .where(WorkspaceMember.user_id == user_id)
        .order_by(Workspace.created_at)
    )
    return list(db.scalars(statement))


def create_workspace(db: Session, owner: User, payload: WorkspaceCreate) -> Workspace:
    """Create a workspace together with the creator's OWNER membership.

    Both rows are written in one commit, so a workspace can never exist
    without an owner to administer it.
    """
    workspace = Workspace(name=payload.name.strip())
    workspace.members.append(WorkspaceMember(user_id=owner.id, role=WorkspaceRole.OWNER))

    db.add(workspace)
    db.commit()

    return workspace


def update_workspace(db: Session, workspace: Workspace, payload: WorkspaceUpdate) -> Workspace:
    workspace.name = payload.name.strip()
    db.commit()

    return workspace


def delete_workspace(db: Session, workspace: Workspace) -> None:
    db.delete(workspace)
    db.commit()
