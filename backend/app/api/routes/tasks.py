from fastapi import APIRouter, status, HTTPException

from app.api.deps import DbSession, ProjectAccess, CurrentUser, TaskAccess
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskRead
from app.services import task_service


router = APIRouter(prefix="/workspaces/{workspace_id}/projects/{project_id}/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: DbSession, access: ProjectAccess, current_user: CurrentUser) -> Task:
    try:
        return task_service.create_task(db, access, current_user, payload)
    except task_service.AssigneeNotInWorkspaceError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Assignee is not in the workspace") from None

@router.get("", response_model=list[TaskRead])
def list_tasks(db: DbSession, access: ProjectAccess) -> list[Task]:
    return task_service.list_tasks(db, access.id)

@router.get("/{task_id}", response_model=TaskRead)
def get_task(task: TaskAccess) -> Task:
    return task
