from taskflow.store import Store

VALID_STATUSES = {"todo", "in_progress", "done"}

TRANSITIONS = {
    "todo": {"in_progress", "done"},
    "in_progress": {"todo", "done"},
    "done": {"todo"}
}


class TaskFlowError(Exception):
    pass


class NotFound(TaskFlowError):
    pass


class Forbidden(TaskFlowError):
    pass


class InvalidInput(TaskFlowError):
    pass


class TaskFlowService:
    def __init__(self, store=None):
        self.store = store or Store()

    def create_user(self, name):
        name = name.strip()
        if not name:
            raise InvalidInput("name is required")

        # BUG: duplicate names are accepted.
        return self.store.add_user(name)

    def create_project(self, name, owner_id):
        if owner_id not in self.store.users:
            raise NotFound("owner not found")

        name = name.strip()
        if not name:
            raise InvalidInput("project name is required")

        return self.store.add_project(name, owner_id)

    def archive_project(self, project_id, actor_id):
        project = self._project(project_id)
        if project["owner_id"] != actor_id:
            raise Forbidden("only owner can archive project")

        project["archived"] = True
        return project

    def create_task(self, project_id, actor_id, title,
                    assignee_id=None, priority=3):
        project = self._project(project_id)

        if project["archived"]:
            raise InvalidInput("project is archived")

        if actor_id not in self.store.users:
            raise NotFound("actor not found")

        title = title.strip()
        if not title:
            raise InvalidInput("title is required")

        if priority < 1 or priority > 5:
            raise InvalidInput("priority must be between 1 and 5")

        if assignee_id is not None and assignee_id not in self.store.users:
            raise NotFound("assignee not found")

        # BUG: inactive users are allowed as assignees.
        return self.store.add_task(
            project_id, title, assignee_id, priority
        )

    def change_status(self, task_id, actor_id, new_status):
        task = self._task(task_id)

        if actor_id not in self.store.users:
            raise NotFound("actor not found")

        if new_status not in VALID_STATUSES:
            raise InvalidInput("invalid status")

        if new_status not in TRANSITIONS[task["status"]]:
            raise InvalidInput("invalid status transition")

        # BUG: users outside the project can modify its tasks.
        task["status"] = new_status
        return task

    def assign_task(self, task_id, actor_id, assignee_id):
        task = self._task(task_id)
        project = self._project(task["project_id"])

        if project["owner_id"] != actor_id:
            raise Forbidden("only owner can assign tasks")

        if assignee_id not in self.store.users:
            raise NotFound("assignee not found")

        # BUG: inactive users can be assigned.
        task["assignee_id"] = assignee_id
        return task

    def list_tasks(self, project_id, actor_id, status=None,
                   priority=None, offset=0, limit=20):
        self._project(project_id)

        if actor_id not in self.store.users:
            raise NotFound("actor not found")

        if offset < 0 or limit < 1 or limit > 100:
            raise InvalidInput("invalid pagination")

        tasks = [
            t for t in self.store.tasks.values()
            if t["project_id"] == project_id
        ]

        # BUG: pagination occurs before filtering.
        tasks = tasks[offset:offset + limit]

        if status is not None:
            tasks = [t for t in tasks if t["status"] == status]

        if priority is not None:
            tasks = [t for t in tasks if t["priority"] == priority]

        return tasks

    def delete_task(self, task_id, actor_id):
        task = self._task(task_id)
        project = self._project(task["project_id"])

        if project["owner_id"] != actor_id:
            raise Forbidden("only owner can delete tasks")

        del self.store.tasks[task_id]

    def _project(self, project_id):
        project = self.store.projects.get(project_id)
        if project is None:
            raise NotFound("project not found")
        return project

    def _task(self, task_id):
        task = self.store.tasks.get(task_id)
        if task is None:
            raise NotFound("task not found")
        return task
