import pytest
from taskflow.service import InvalidInput, Forbidden, NotFound


def test_create_task_trims_title(setup_service):
    s, owner, member, _, p = setup_service
    t = s.create_task(p["id"], owner["id"], "  Fix login  ", member["id"])
    assert t["title"] == "Fix login"


def test_blank_title_rejected(setup_service):
    s, owner, _, _, p = setup_service
    with pytest.raises(InvalidInput, match="title"):
        s.create_task(p["id"], owner["id"], "   ")


def test_unknown_assignee_rejected(setup_service):
    s, owner, _, _, p = setup_service
    with pytest.raises(NotFound, match="assignee"):
        s.create_task(p["id"], owner["id"], "Task", 999)


def test_invalid_priority_rejected(setup_service):
    s, owner, _, _, p = setup_service
    with pytest.raises(InvalidInput, match="priority"):
        s.create_task(p["id"], owner["id"], "Task", priority=8)


def test_default_status_is_todo(setup_service):
    s, owner, _, _, p = setup_service
    assert s.create_task(p["id"], owner["id"], "Task")["status"] == "todo"


def test_priority_is_preserved(setup_service):
    s, owner, _, _, p = setup_service
    assert s.create_task(p["id"], owner["id"], "Urgent", priority=1)["priority"] == 1


def test_archived_project_rejects_tasks(setup_service):
    s, owner, _, _, p = setup_service
    s.archive_project(p["id"], owner["id"])
    with pytest.raises(InvalidInput, match="archived"):
        s.create_task(p["id"], owner["id"], "Task")


def test_non_owner_cannot_archive(setup_service):
    s, _, member, _, p = setup_service
    with pytest.raises(Forbidden):
        s.archive_project(p["id"], member["id"])


def test_unknown_project_rejected(setup_service):
    s, owner, _, _, _ = setup_service
    with pytest.raises(NotFound):
        s.create_task(999, owner["id"], "Task")


def test_unknown_actor_rejected(setup_service):
    s, _, _, _, p = setup_service
    with pytest.raises(NotFound, match="actor"):
        s.create_task(p["id"], 999, "Task")


def test_valid_status_transition(setup_service):
    s, owner, _, _, p = setup_service
    t = s.create_task(p["id"], owner["id"], "Task")
    assert s.change_status(t["id"], owner["id"], "in_progress")["status"] == "in_progress"


def test_invalid_status_rejected(setup_service):
    s, owner, _, _, p = setup_service
    t = s.create_task(p["id"], owner["id"], "Task")
    with pytest.raises(InvalidInput, match="invalid status"):
        s.change_status(t["id"], owner["id"], "blocked")


def test_done_cannot_jump_to_in_progress(setup_service):
    s, owner, _, _, p = setup_service
    t = s.create_task(p["id"], owner["id"], "Task")
    s.change_status(t["id"], owner["id"], "done")
    with pytest.raises(InvalidInput, match="transition"):
        s.change_status(t["id"], owner["id"], "in_progress")


def test_outsider_cannot_change_status(setup_service):
    s, owner, _, outsider, p = setup_service
    t = s.create_task(p["id"], owner["id"], "Private task")
    with pytest.raises(Forbidden):
        s.change_status(t["id"], outsider["id"], "in_progress")


def test_non_owner_cannot_delete(setup_service):
    s, owner, member, _, p = setup_service
    t = s.create_task(p["id"], owner["id"], "Task")
    with pytest.raises(Forbidden):
        s.delete_task(t["id"], member["id"])


def test_owner_can_delete(setup_service):
    s, owner, _, _, p = setup_service
    t = s.create_task(p["id"], owner["id"], "Task")
    s.delete_task(t["id"], owner["id"])
    with pytest.raises(NotFound):
        s.change_status(t["id"], owner["id"], "done")


def test_filter_by_status(setup_service):
    s, owner, _, _, p = setup_service
    a = s.create_task(p["id"], owner["id"], "A")
    b = s.create_task(p["id"], owner["id"], "B")
    s.change_status(b["id"], owner["id"], "in_progress")
    assert [t["title"] for t in s.list_tasks(p["id"], owner["id"], status="todo")] == ["A"]


def test_filter_by_priority(setup_service):
    s, owner, _, _, p = setup_service
    s.create_task(p["id"], owner["id"], "Normal", priority=3)
    s.create_task(p["id"], owner["id"], "Urgent", priority=1)
    assert [t["title"] for t in s.list_tasks(p["id"], owner["id"], priority=1)] == ["Urgent"]


def test_filter_happens_before_pagination(setup_service):
    s, owner, _, _, p = setup_service
    s.create_task(p["id"], owner["id"], "Normal", priority=3)
    s.create_task(p["id"], owner["id"], "Urgent 1", priority=1)
    s.create_task(p["id"], owner["id"], "Urgent 2", priority=1)
    result = s.list_tasks(p["id"], owner["id"], priority=1, limit=1)
    assert [t["title"] for t in result] == ["Urgent 1"]


def test_negative_offset_rejected(setup_service):
    s, owner, _, _, p = setup_service
    with pytest.raises(InvalidInput, match="pagination"):
        s.list_tasks(p["id"], owner["id"], offset=-1)


def test_limit_over_100_rejected(setup_service):
    s, owner, _, _, p = setup_service
    with pytest.raises(InvalidInput, match="pagination"):
        s.list_tasks(p["id"], owner["id"], limit=101)


def test_owner_can_assign_task(setup_service):
    s, owner, member, _, p = setup_service
    t = s.create_task(p["id"], owner["id"], "Task")
    assert s.assign_task(t["id"], owner["id"], member["id"])["assignee_id"] == member["id"]


def test_non_owner_cannot_assign(setup_service):
    s, owner, member, _, p = setup_service
    t = s.create_task(p["id"], owner["id"], "Task")
    with pytest.raises(Forbidden):
        s.assign_task(t["id"], member["id"], member["id"])


def test_duplicate_user_name_rejected(setup_service):
    s, _, _, _, _ = setup_service
    with pytest.raises(InvalidInput, match="already exists"):
        s.create_user("owner")


def test_project_name_required(setup_service):
    s, owner, _, _, _ = setup_service
    with pytest.raises(InvalidInput, match="project name"):
        s.create_project("  ", owner["id"])


def test_missing_task_rejected(setup_service):
    s, owner, _, _, _ = setup_service
    with pytest.raises(NotFound, match="task"):
        s.change_status(999, owner["id"], "done")


def test_unknown_status_does_not_change_task(setup_service):
    s, owner, _, _, p = setup_service
    t = s.create_task(p["id"], owner["id"], "Task")
    with pytest.raises(InvalidInput):
        s.change_status(t["id"], owner["id"], "invalid")
    assert t["status"] == "todo"
