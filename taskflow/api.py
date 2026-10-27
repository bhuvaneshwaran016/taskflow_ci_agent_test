from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from taskflow.service import (
    TaskFlowService, TaskFlowError, NotFound, Forbidden, InvalidInput
)

app = FastAPI(title="TaskFlow API")
service = TaskFlowService()


class UserInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    owner_id: int


class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    actor_id: int
    assignee_id: int | None = None
    priority: int = Field(default=3, ge=1, le=5)


class StatusInput(BaseModel):
    actor_id: int
    status: str


def handle_error(exc):
    if isinstance(exc, NotFound):
        code = 404
    elif isinstance(exc, Forbidden):
        code = 403
    elif isinstance(exc, InvalidInput):
        code = 400
    else:
        code = 500

    raise HTTPException(status_code=code, detail=str(exc))


@app.post("/users", status_code=201)
def create_user(payload: UserInput):
    try:
        user = service.create_user(payload.name)
        return user
    except TaskFlowError as exc:
        handle_error(exc)


@app.post("/projects", status_code=201)
def create_project(payload: ProjectInput):
    try:
        return service.create_project(payload.name, payload.owner_id)
    except TaskFlowError as exc:
        handle_error(exc)


@app.post("/projects/{project_id}/tasks", status_code=201)
def create_task(project_id: int, payload: TaskInput):
    try:
        return service.create_task(
            project_id, payload.actor_id, payload.title,
            payload.assignee_id, payload.priority
        )
    except TaskFlowError as exc:
        handle_error(exc)


@app.patch("/tasks/{task_id}/status")
def change_status(task_id: int, payload: StatusInput):
    try:
        return service.change_status(
            task_id, payload.actor_id, payload.status
        )
    except TaskFlowError as exc:
        handle_error(exc)


@app.get("/projects/{project_id}/tasks")
def list_tasks(
    project_id: int,
    actor_id: int,
    status: str | None = None,
    priority: int | None = None,
    offset: int = Query(default=0),
    limit: int = Query(default=20)
):
    try:
        items = service.list_tasks(
            project_id, actor_id, status, priority, offset, limit
        )
        return {"items": items, "count": len(items)}
    except TaskFlowError as exc:
        handle_error(exc)
