import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.models.project import Project
from app.models.user import User

if TYPE_CHECKING:
    from app.models.activity import TaskActivity


class TaskStatus(StrEnum):
    BACKLOG = "BACKLOG"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"


class TaskPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskType(StrEnum):
    FEATURE = "FEATURE"
    BUG = "BUG"
    CHORE = "CHORE"
    TEST = "TEST"
    DOCS = "DOCS"


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    __table_args__ = (UniqueConstraint("project_id", "number"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
    )
    # Sequential within the project. Paired with the project key this gives
    # the readable identifier, DEV-42, which is never the primary key.
    number: Mapped[int]
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status"),
        server_default=TaskStatus.BACKLOG.value,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority"),
        server_default=TaskPriority.MEDIUM.value,
    )
    type: Mapped[TaskType] = mapped_column(
        Enum(TaskType, name="task_type"),
        server_default=TaskType.FEATURE.value,
    )
    # Who filed it. RESTRICT because the timeline should not lose its author;
    # there is no user deletion endpoint, so nothing is blocked in practice.
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    project: Mapped[Project] = relationship(back_populates="tasks")
    reporter: Mapped[User] = relationship(foreign_keys=[reporter_id])
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id])
    activities: Mapped[list["TaskActivity"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )

    @property
    def key(self) -> str:
        return f"{self.project.key}-{self.number}"
