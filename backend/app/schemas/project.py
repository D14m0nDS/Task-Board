import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Letters only, so a task identifier like DEV-42 can never be read two ways
# when it is parsed out of a branch name or commit message later.
KEY_PATTERN = r"^[A-Z]{2,10}$"


class ProjectCreate(BaseModel):
    key: str = Field(pattern=KEY_PATTERN)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None

    @field_validator("key", mode="before")
    @classmethod
    def normalise_key(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


class ProjectUpdate(BaseModel):
    """The key is deliberately absent: changing it would rename every task."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    key: str
    name: str
    description: str | None
    created_at: datetime
