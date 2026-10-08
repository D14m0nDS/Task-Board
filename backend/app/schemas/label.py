import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"


class LabelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    color: str = Field(default="#6B7280", pattern=COLOR_PATTERN)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name cannot be blank")
        return stripped

    @field_validator("color")
    @classmethod
    def normalise_color(cls, value: str) -> str:
        return value.upper()


class LabelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    color: str


class TaskLabelsUpdate(BaseModel):
    """The full set of labels on a task. An empty list clears them."""

    label_ids: list[uuid.UUID]
