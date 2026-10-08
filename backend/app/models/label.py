import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Index, String, Table, func, literal_column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.task import Task

# Association only. A task carries labels; the row has no data of its own.
task_labels = Table(
    "task_labels",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("label_id", ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True),
)


class Label(Base, TimestampMixin):
    """A tag defined on one project and applied to that project's tasks."""

    __tablename__ = "labels"
    # Case-insensitive per project, so "Bug" and "bug" cannot both exist.
    __table_args__ = (
        Index(
            "uq_labels_project_id_name",
            "project_id",
            func.lower(literal_column("name")),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
    )
    name: Mapped[str] = mapped_column(String(40))
    color: Mapped[str] = mapped_column(String(7))

    tasks: Mapped[list["Task"]] = relationship(
        secondary=task_labels,
        back_populates="labels",
    )
