import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.label import Label
from app.models.project import Project
from app.models.task import Task
from app.schemas.label import LabelCreate


class LabelNameTakenError(Exception):
    """This project already has a label with this name."""


class LabelNotOnProjectError(Exception):
    """A label id does not belong to the task's project."""


def list_labels(db: Session, project_id: uuid.UUID) -> list[Label]:
    statement = (
        select(Label).where(Label.project_id == project_id).order_by(func.lower(Label.name))
    )
    return list(db.scalars(statement))


def create_label(db: Session, project: Project, payload: LabelCreate) -> Label:
    existing = db.scalar(
        select(Label).where(
            Label.project_id == project.id,
            func.lower(Label.name) == payload.name.lower(),
        )
    )
    if existing is not None:
        raise LabelNameTakenError(payload.name)

    label = Label(project_id=project.id, name=payload.name, color=payload.color)
    db.add(label)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise LabelNameTakenError(payload.name) from exc

    return label


def set_task_labels(db: Session, task: Task, label_ids: list[uuid.UUID]) -> Task:
    """Replace the task's labels with this set.

    Every id must already be a label on the same project. Ids from another
    project do not resolve, so they cannot be attached by guessing.
    """
    wanted = list(dict.fromkeys(label_ids))
    if wanted:
        found = list(
            db.scalars(
                select(Label).where(Label.project_id == task.project_id, Label.id.in_(wanted))
            )
        )
    else:
        found = []

    if len(found) != len(wanted):
        raise LabelNotOnProjectError(task.project_id)

    by_id = {label.id: label for label in found}
    task.labels = [by_id[label_id] for label_id in wanted]
    db.commit()

    return task
