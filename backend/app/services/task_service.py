import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import ActivitySource, ActivityType, TaskActivity
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
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


def _record(
    db: Session,
    task: Task,
    actor: User | None,
    activity_type: ActivityType,
    data: dict,
) -> None:
    db.add(
        TaskActivity(
            task_id=task.id,
            actor_id=None if actor is None else actor.id,
            source=ActivitySource.USER,
            type=activity_type,
            data=data,
        )
    )


def _require_workspace_member(db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
    membership = workspace_service.get_membership(db, workspace_id, user_id)
    if membership is None:
        raise AssigneeNotInWorkspaceError(user_id)


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
        _require_workspace_member(db, project.workspace_id, payload.assignee_id)

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
    db.flush()

    _record(db, task, reporter, ActivityType.TASK_CREATED, {"status": task.status.value})
    if task.assignee_id is not None:
        _record(
            db,
            task,
            reporter,
            ActivityType.USER_ASSIGNED,
            {"from": None, "to": str(task.assignee_id)},
        )

    db.commit()

    return task


def list_task_activity(db: Session, task_id: uuid.UUID) -> list[TaskActivity]:
    statement = (
        select(TaskActivity).where(TaskActivity.task_id == task_id).order_by(TaskActivity.seq)
    )
    return list(db.scalars(statement))


def update_task(db: Session, task: Task, actor: User, payload: TaskUpdate) -> Task:
    """Apply a partial update and record the changes the timeline cares about.

    Title, description, priority and type are stored on the task. Status and
    assignee also produce an activity row, and only when the value actually
    changes.
    """
    changes = payload.model_dump(exclude_unset=True)

    if "assignee_id" in changes and changes["assignee_id"] is not None:
        _require_workspace_member(db, task.project.workspace_id, changes["assignee_id"])

    if "title" in changes and changes["title"] is not None:
        task.title = changes["title"]

    if "description" in changes:
        task.description = changes["description"]

    if "priority" in changes and changes["priority"] is not None:
        task.priority = changes["priority"]

    if "type" in changes and changes["type"] is not None:
        task.type = changes["type"]

    if "status" in changes and changes["status"] is not None and changes["status"] != task.status:
        _record(
            db,
            task,
            actor,
            ActivityType.STATUS_CHANGED,
            {"from": task.status.value, "to": changes["status"].value},
        )
        task.status = changes["status"]

    if "assignee_id" in changes and changes["assignee_id"] != task.assignee_id:
        previous = None if task.assignee_id is None else str(task.assignee_id)
        new = None if changes["assignee_id"] is None else str(changes["assignee_id"])
        _record(
            db,
            task,
            actor,
            ActivityType.USER_ASSIGNED,
            {"from": previous, "to": new},
        )
        task.assignee_id = changes["assignee_id"]

    db.commit()

    return task
