class Store:
    def __init__(self):
        self.users = {}
        self.projects = {}
        self.tasks = {}
        self.next_user_id = 1
        self.next_project_id = 1
        self.next_task_id = 1

    def add_user(self, name):
        user = {
            "id": self.next_user_id,
            "name": name,
            "active": True
        }
        self.users[user["id"]] = user
        self.next_user_id += 1
        return user

    def add_project(self, name, owner_id):
        project = {
            "id": self.next_project_id,
            "name": name,
            "owner_id": owner_id,
            "archived": False
        }
        self.projects[project["id"]] = project
        self.next_project_id += 1
        return project

    def add_task(self, project_id, title, assignee_id=None, priority=3):
        task = {
            "id": self.next_task_id,
            "project_id": project_id,
            "title": title,
            "assignee_id": assignee_id,
            "priority": priority,
            "status": "todo"
        }
        self.tasks[task["id"]] = task
        self.next_task_id += 1
        return task
