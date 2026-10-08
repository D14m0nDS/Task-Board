# Every model must be imported here. Alembic autogenerate only sees tables
# that have been registered on Base.metadata by an actual import.

from app.models.user import User  # noqa: F401
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.task import Task, TaskPriority, TaskStatus, TaskType  # noqa: F401