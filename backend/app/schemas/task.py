import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.activity import ActivitySource, ActivityType
from app.models.task import TaskPriority, TaskStatus, TaskType
from app.schemas.label import LabelRead
from app.schemas.user import UserRead


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus = TaskStatus.BACKLOG
    priority: TaskPriority = TaskPriority.MEDIUM
    type: TaskType = TaskType.FEATURE
    assignee_id: uuid.UUID | None = None


class TaskUpdate(BaseModel):
    """Omitted fields stay as they are. Null clears description and assignee."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    type: TaskType | None = None
    assignee_id: uuid.UUID | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("title cannot be blank")
        return stripped


class TaskActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: ActivityType
    source: ActivitySource
    actor: UserRead | None
    data: dict
    created_at: datetime


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    number: int
    # Derived, DEV-42. Not a column, so it cannot drift from the project key.
    key: str
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    type: TaskType
    reporter: UserRead
    assignee: UserRead | None
    labels: list[LabelRead]
    created_at: datetime
