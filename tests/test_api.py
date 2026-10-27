def test_create_user_api(client):
    r = client.post("/users", json={"name": "Ravi"})
    assert r.status_code == 201
    assert r.json()["name"] == "Ravi"


def test_duplicate_user_api_returns_400(client):
    client.post("/users", json={"name": "Ravi"})
    r = client.post("/users", json={"name": "ravi"})
    assert r.status_code == 400


def test_project_requires_existing_owner(client):
    r = client.post("/projects", json={"name": "Website", "owner_id": 999})
    assert r.status_code == 404


def test_create_and_list_task_api(client):
    user = client.post("/users", json={"name": "Owner"}).json()
    project = client.post(
        "/projects",
        json={"name": "Website", "owner_id": user["id"]}
    ).json()
    created = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "Fix bug", "actor_id": user["id"]}
    )
    assert created.status_code == 201
    listed = client.get(
        f"/projects/{project['id']}/tasks",
        params={"actor_id": user["id"]}
    )
    assert listed.status_code == 200
    assert listed.json()["count"] == 1


def test_api_rejects_invalid_priority(client):
    user = client.post("/users", json={"name": "Owner"}).json()
    project = client.post(
        "/projects",
        json={"name": "Website", "owner_id": user["id"]}
    ).json()
    r = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "Task", "actor_id": user["id"], "priority": 9}
    )
    assert r.status_code == 422
