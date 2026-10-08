import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Identity
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.models.user import User

if TYPE_CHECKING:
    from app.models.task import Task


class ActivitySource(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    GITHUB = "GITHUB"


class ActivityType(StrEnum):
    TASK_CREATED = "TASK_CREATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    USER_ASSIGNED = "USER_ASSIGNED"


class TaskActivity(Base, TimestampMixin):
    """One structured event on a task timeline.

    `data` holds the facts of the event, such as {"from": "BACKLOG", "to":
    "IN_PROGRESS"}. The readable sentence is derived from that, not stored.
    """

    __tablename__ = "task_activities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Identity so two events written in one transaction still have a stable order.
    # Postgres now() does not move inside a transaction.
    seq: Mapped[int] = mapped_column(Identity(), unique=True)
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        index=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    source: Mapped[ActivitySource] = mapped_column(
        Enum(ActivitySource, name="task_activity_source"),
    )
    type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, name="task_activity_type"),
    )
    data: Mapped[dict] = mapped_column(JSONB)

    task: Mapped["Task"] = relationship(back_populates="activities")
    actor: Mapped[User | None] = relationship()
