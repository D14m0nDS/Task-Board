import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskPriority, TaskStatus, TaskType
from app.schemas.user import UserRead


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus = TaskStatus.BACKLOG
    priority: TaskPriority = TaskPriority.MEDIUM
    type: TaskType = TaskType.FEATURE
    assignee_id: uuid.UUID | None = None


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
    created_at: datetime
