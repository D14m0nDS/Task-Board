import uuid
from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.services import project_service, user_service, workspace_service

# auto_error=False so a missing header reaches our code and produces a 401;
# the default behaviour would return 403, which is misleading here.
bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """One session per request, always closed.

    Committing is left to the service layer so a request can span several
    writes and still fail as a single unit.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """Resolve the bearer token into a user, or reject the request.

    Every failure returns the same message so the response cannot be used to
    probe which user ids or emails exist.
    """
    if credentials is None:
        raise _unauthorized()

    try:
        subject = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(subject)
    except (jwt.InvalidTokenError, ValueError):
        raise _unauthorized() from None

    user = user_service.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise _unauthorized()

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_workspace_membership(
    workspace_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> WorkspaceMember:
    """Resolve the workspace in the path into the caller's membership.

    A non-member gets 404 rather than 403, so the API never confirms that a
    workspace exists to someone who has no business knowing.
    """
    membership = workspace_service.get_membership(db, workspace_id, current_user.id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    return membership


WorkspaceMembership = Annotated[WorkspaceMember, Depends(get_workspace_membership)]


def get_workspace_ownership(membership: WorkspaceMembership) -> WorkspaceMember:
    """Same, but restricted to owners.

    403 is right here: a member already knows the workspace exists, so the
    only new information is that they lack the role.
    """
    if membership.role != WorkspaceRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires the workspace owner role",
        )

    return membership


WorkspaceOwnership = Annotated[WorkspaceMember, Depends(get_workspace_ownership)]


def _resolve_project(db: Session, workspace_id: uuid.UUID, project_id: uuid.UUID) -> Project:
    project = project_service.get_project(db, workspace_id, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


def get_workspace_project(
    project_id: uuid.UUID,
    db: DbSession,
    membership: WorkspaceMembership,
) -> Project:
    """The project named in the path, once the caller is known to be a member.

    The workspace dependency has already answered the harder question, so a
    project id from another workspace just fails to resolve here.
    """
    return _resolve_project(db, membership.workspace_id, project_id)


ProjectAccess = Annotated[Project, Depends(get_workspace_project)]


def get_owned_workspace_project(
    project_id: uuid.UUID,
    db: DbSession,
    membership: WorkspaceOwnership,
) -> Project:
    return _resolve_project(db, membership.workspace_id, project_id)


ProjectOwnership = Annotated[Project, Depends(get_owned_workspace_project)]
