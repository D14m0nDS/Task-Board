import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.models.workspace import Workspace


class Project(Base, TimestampMixin):
    """A project inside a workspace. Its key prefixes task ids, e.g. DEV-42."""

    __tablename__ = "projects"
    # Unique per workspace rather than globally, so two workspaces can each
    # have a project keyed DEV. The trailing comma makes this a tuple.
    __table_args__ = (UniqueConstraint("workspace_id", "key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
    )
    key: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)

    workspace: Mapped[Workspace] = relationship(back_populates="projects")
