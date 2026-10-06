import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.workspace import Workspace
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectKeyTakenError(Exception):
    """The workspace already has a project with this key."""


def get_project(db: Session, workspace_id: uuid.UUID, project_id: uuid.UUID) -> Project | None:
    """Look the project up within its workspace.

    Scoping the query means a project id belonging to another workspace simply
    does not resolve, so the caller's workspace permissions cannot be sidestepped
    by guessing an id.
    """
    statement = select(Project).where(
        Project.id == project_id,
        Project.workspace_id == workspace_id,
    )
    return db.scalar(statement)


def list_projects(db: Session, workspace_id: uuid.UUID) -> list[Project]:
    statement = (
        select(Project).where(Project.workspace_id == workspace_id).order_by(Project.key)
    )
    return list(db.scalars(statement))


def create_project(db: Session, workspace: Workspace, payload: ProjectCreate) -> Project:
    existing = db.scalar(
        select(Project).where(
            Project.workspace_id == workspace.id,
            Project.key == payload.key,
        )
    )
    if existing is not None:
        raise ProjectKeyTakenError(payload.key)

    project = Project(
        workspace_id=workspace.id,
        key=payload.key,
        name=payload.name.strip(),
        description=payload.description,
    )
    db.add(project)

    try:
        db.commit()
    except IntegrityError as exc:
        # The unique index on (workspace_id, key) is the only real guard
        # against two concurrent creates.
        db.rollback()
        raise ProjectKeyTakenError(payload.key) from exc

    return project


def update_project(db: Session, project: Project, payload: ProjectUpdate) -> Project:
    changes = payload.model_dump(exclude_unset=True)

    if changes.get("name") is not None:
        project.name = changes["name"].strip()

    if "description" in changes:
        project.description = changes["description"]

    db.commit()

    return project
