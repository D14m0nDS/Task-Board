import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate
from app.services import user_service


class UserNotFoundError(Exception):
    """No account exists for the email given."""


class AlreadyAMemberError(Exception):
    """The user already belongs to the workspace."""


class NotAMemberError(Exception):
    """The user does not belong to the workspace."""


class LastOwnerError(Exception):
    """The change would leave the workspace with no owner."""


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


def _reject_if_last_owner(db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Refuse a change that would strand the workspace with nobody to run it.

    The owner rows are locked for the rest of the transaction, so two owners
    cannot each observe the other and both step down.
    """
    statement = (
        select(WorkspaceMember.user_id)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.role == WorkspaceRole.OWNER,
        )
        .with_for_update()
    )
    owner_ids = list(db.scalars(statement))

    if owner_ids == [user_id]:
        raise LastOwnerError(user_id)


def add_member(
    db: Session, workspace: Workspace, email: str, role: WorkspaceRole
) -> WorkspaceMember:
    user = user_service.get_user_by_email(db, email)
    if user is None:
        raise UserNotFoundError(email)

    if get_membership(db, workspace.id, user.id) is not None:
        raise AlreadyAMemberError(email)

    membership = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=role)
    db.add(membership)

    try:
        db.commit()
    except IntegrityError as exc:
        # The composite primary key is the only real guard against two
        # concurrent adds for the same user.
        db.rollback()
        raise AlreadyAMemberError(email) from exc

    return membership


def change_member_role(
    db: Session, workspace: Workspace, user_id: uuid.UUID, role: WorkspaceRole
) -> WorkspaceMember:
    membership = get_membership(db, workspace.id, user_id)
    if membership is None:
        raise NotAMemberError(user_id)

    if role != WorkspaceRole.OWNER:
        _reject_if_last_owner(db, workspace.id, user_id)

    membership.role = role
    db.commit()

    return membership


def remove_member(db: Session, workspace: Workspace, user_id: uuid.UUID) -> None:
    membership = get_membership(db, workspace.id, user_id)
    if membership is None:
        raise NotAMemberError(user_id)

    _reject_if_last_owner(db, workspace.id, user_id)

    db.delete(membership)
    db.commit()
