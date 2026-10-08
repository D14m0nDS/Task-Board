import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate
from app.services import workspace_service


class AssigneeNotInWorkspaceError(Exception):
    """The chosen assignee is not a member of the project's workspace."""


def allocate_task_number(db: Session, project_id: uuid.UUID) -> int:
    """Take the next task number for a project.

    The project row is locked for the rest of the transaction, so a second
    create waits here rather than reading the same counter. Deliberately does
    not commit: the number and the task it belongs to must be written as one
    unit, or a failed insert would burn a number.
    """
    statement = select(Project).where(Project.id == project_id).with_for_update()
    project = db.scalars(statement).one()

    number = project.next_task_number
    project.next_task_number = number + 1
    db.flush()

    return number


def get_task(db: Session, project_id: uuid.UUID, task_id: uuid.UUID) -> Task | None:
    """Look the task up within its project, so an id from elsewhere does not resolve."""
    statement = select(Task).where(Task.id == task_id, Task.project_id == project_id)
    return db.scalar(statement)


def list_tasks(db: Session, project_id: uuid.UUID) -> list[Task]:
    statement = select(Task).where(Task.project_id == project_id).order_by(Task.number)
    return list(db.scalars(statement))


def create_task(db: Session, project: Project, reporter: User, payload: TaskCreate) -> Task:
    """File a task and take the next number in the same transaction.

    Any workspace member may call this. The number is allocated under a row
    lock and committed together with the insert, so a failed create does not
    leave a gap and two creates cannot share a number.
    """
    if payload.assignee_id is not None:
        membership = workspace_service.get_membership(
            db, project.workspace_id, payload.assignee_id
        )
        if membership is None:
            raise AssigneeNotInWorkspaceError(payload.assignee_id)

    task = Task(
        project_id=project.id,
        number=allocate_task_number(db, project.id),
        title=payload.title.strip(),
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        type=payload.type,
        reporter_id=reporter.id,
        assignee_id=payload.assignee_id,
    )
    db.add(task)
    db.commit()

    return task
