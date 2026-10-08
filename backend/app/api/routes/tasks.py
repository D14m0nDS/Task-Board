from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, ProjectAccess, TaskAccess
from app.models.activity import TaskActivity
from app.models.task import Task
from app.schemas.task import TaskActivityRead, TaskCreate, TaskRead, TaskUpdate
from app.services import task_service, label_service
from app.models.label import Label
from app.schemas.label import LabelRead, TaskLabelsUpdate

router = APIRouter(
    prefix="/workspaces/{workspace_id}/projects/{project_id}/tasks",
    tags=["tasks"],
)


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate, db: DbSession, project: ProjectAccess, current_user: CurrentUser
) -> Task:
    try:
        return task_service.create_task(db, project, current_user, payload)
    except task_service.AssigneeNotInWorkspaceError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Assignee is not in the workspace",
        ) from None


@router.get("", response_model=list[TaskRead])
def list_tasks(db: DbSession, project: ProjectAccess) -> list[Task]:
    return task_service.list_tasks(db, project.id)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task: TaskAccess) -> Task:
    return task


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    payload: TaskUpdate, db: DbSession, task: TaskAccess, current_user: CurrentUser
) -> Task:
    try:
        return task_service.update_task(db, task, current_user, payload)
    except task_service.AssigneeNotInWorkspaceError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Assignee is not in the workspace",
        ) from None


@router.get("/{task_id}/activity", response_model=list[TaskActivityRead])
def list_task_activity(db: DbSession, task: TaskAccess) -> list[TaskActivity]:
    return task_service.list_task_activity(db, task.id)


@router.put("/{task_id}/labels", response_model=TaskRead)
def set_task_labels(db: DbSession, task: TaskAccess, payload: TaskLabelsUpdate) -> Task:
    try:
        return label_service.set_task_labels(db, task, payload.label_ids)
    except label_service.LabelNotOnProjectError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="One or more labels are not on this project",
        ) from None