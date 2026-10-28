import datetime
import pytest
from taskflow.service import InvalidInput, Forbidden, NotFound


# =============================================================================
# 1. Task Search Tests (Passing + Failing)
# =============================================================================

def test_search_tasks_by_title_case_insensitive(setup_service):
    s, owner, _, _, p = setup_service
    s.create_task(p["id"], owner["id"], "Fix Authentication Header")
    s.create_task(p["id"], owner["id"], "Update Database Schema")
    results = s.search_tasks(p["id"], owner["id"], "authentication")
    assert len(results) == 1
    assert results[0]["title"] == "Fix Authentication Header"


def test_search_tasks_blank_query_rejected(setup_service):
    s, owner, _, _, p = setup_service
    with pytest.raises(InvalidInput, match="query"):
        s.search_tasks(p["id"], owner["id"], "   ")


def test_search_tasks_no_match_returns_empty(setup_service):
    s, owner, _, _, p = setup_service
    s.create_task(p["id"], owner["id"], "Fix Login")
    results = s.search_tasks(p["id"], owner["id"], "billing")
    assert results == []


def test_search_matches_description(setup_service):
    """
    Search should find tasks matching the keyword in title OR description.
    """
    s, owner, _, _, p = setup_service
    t = s.create_task(
        p["id"], owner["id"],
        title="Bug Ticket 101",
        description="User encounter OAuth2 token expiration error"
    )
    results = s.search_tasks(p["id"], owner["id"], "OAuth2")
    assert len(results) == 1
    assert results[0]["id"] == t["id"]


@pytest.mark.parametrize("query,desc", [
    ("oauth", "Integration error with oauth provider"),
    ("postgres", "Optimize slow postgres database queries"),
    ("billing", "Fix recurring billing payment gateway retry"),
    ("docker", "Update Dockerfile to multi-stage build"),
    ("redis", "Configure redis caching layer for session"),
    ("graphql", "Implement new graphql mutation for tasks"),
    ("kubernetes", "Deploy ingress controller to kubernetes"),
    ("timeout", "Increase gateway request timeout threshold"),
], ids=[
    "oauth_desc",
    "postgres_desc",
    "billing_desc",
    "docker_desc",
    "redis_desc",
    "graphql_desc",
    "kubernetes_desc",
    "timeout_desc",
])
def test_search_matches_description_parametrized(setup_service, query, desc):
    """
    Search must match keywords appearing in task description.
    """
    s, owner, _, _, p = setup_service
    t = s.create_task(p["id"], owner["id"], title="Internal Ticket #404", description=desc)
    matches = s.search_tasks(p["id"], owner["id"], query)
    assert len(matches) == 1
    assert matches[0]["id"] == t["id"]


# =============================================================================
# 2. Task Priority Filtering Tests (Passing + Failing)
# =============================================================================

def test_filter_by_numeric_priority(setup_service):
    s, owner, _, _, p = setup_service
    s.create_task(p["id"], owner["id"], "Urgent", priority=1)
    s.create_task(p["id"], owner["id"], "Normal", priority=3)
    s.create_task(p["id"], owner["id"], "Trivial", priority=5)

    high = s.filter_tasks_by_priority(p["id"], owner["id"], 1)
    assert [t["title"] for t in high] == ["Urgent"]

    normal = s.filter_tasks_by_priority(p["id"], owner["id"], 3)
    assert [t["title"] for t in normal] == ["Normal"]


def test_filter_by_named_priority_medium(setup_service):
    s, owner, _, _, p = setup_service
    s.create_task(p["id"], owner["id"], "P1", priority=1)
    s.create_task(p["id"], owner["id"], "P3", priority=3)
    medium_tasks = s.filter_tasks_by_priority(p["id"], owner["id"], "medium")
    assert [t["title"] for t in medium_tasks] == ["P3"]


def test_filter_by_priority_invalid_rejected(setup_service):
    s, owner, _, _, p = setup_service
    with pytest.raises(InvalidInput):
        s.filter_tasks_by_priority(p["id"], owner["id"], "critical")


@pytest.mark.parametrize("named_p,task_priority,title", [
    ("high", 2, "High-P2-A"),
    ("high", 2, "High-P2-B"),
    ("high", 2, "High-P2-C"),
    ("low", 4, "Low-P4-A"),
    ("low", 4, "Low-P4-B"),
    ("low", 4, "Low-P4-C"),
], ids=[
    "high_includes_p2_first",
    "high_includes_p2_second",
    "high_includes_p2_third",
    "low_includes_p4_first",
    "low_includes_p4_second",
    "low_includes_p4_third",
])
def test_filter_priority_named_range_includes_boundary(setup_service, named_p, task_priority, title):
    """
    High priority should include priority 1 and 2.
    Low priority should include priority 4 and 5.
    """
    s, owner, _, _, p = setup_service
    s.create_task(p["id"], owner["id"], title, priority=task_priority)
    results = s.filter_tasks_by_priority(p["id"], owner["id"], named_p)
    assert title in [t["title"] for t in results]


# =============================================================================
# 3. Task Due-Date Filtering Tests (Passing + Failing)
# =============================================================================

def test_due_date_invalid_format_rejected(setup_service):
    s, owner, _, _, p = setup_service
    with pytest.raises(InvalidInput, match="due_date"):
        s.create_task(p["id"], owner["id"], "Task", due_date="28-10-2026")


def test_overdue_tasks_returns_past_due(setup_service):
    s, owner, _, _, p = setup_service
    s.create_task(p["id"], owner["id"], "Past Due", due_date="2026-10-01")
    s.create_task(p["id"], owner["id"], "Future Task", due_date="2026-11-01")

    overdue = s.get_overdue_tasks(p["id"], owner["id"], as_of_date="2026-10-28")
    assert [t["title"] for t in overdue] == ["Past Due"]


def test_overdue_tasks_ignores_completed(setup_service):
    s, owner, _, _, p = setup_service
    t = s.create_task(p["id"], owner["id"], "Completed Task", due_date="2026-10-01")
    s.change_status(t["id"], owner["id"], "done")

    overdue = s.get_overdue_tasks(p["id"], owner["id"], as_of_date="2026-10-28")
    assert overdue == []


def test_tasks_due_within_days(setup_service):
    s, owner, _, _, p = setup_service
    s.create_task(p["id"], owner["id"], "Due Soon", due_date="2026-10-30")
    s.create_task(p["id"], owner["id"], "Due Far", due_date="2026-11-20")

    due_soon = s.get_tasks_due_within(p["id"], owner["id"], days=5, as_of_date="2026-10-28")
    assert [t["title"] for t in due_soon] == ["Due Soon"]


def test_tasks_due_within_negative_days_rejected(setup_service):
    s, owner, _, _, p = setup_service
    with pytest.raises(InvalidInput, match="non-negative"):
        s.get_tasks_due_within(p["id"], owner["id"], days=-3)


def test_overdue_tasks_boundary_today_not_overdue(setup_service):
    """
    A task whose due_date is today (as_of_date) is due today, NOT overdue.
    Only tasks with due_date strictly before as_of_date should be overdue.
    """
    s, owner, _, _, p = setup_service
    s.create_task(p["id"], owner["id"], "Due Today", due_date="2026-10-28")

    overdue = s.get_overdue_tasks(p["id"], owner["id"], as_of_date="2026-10-28")
    assert overdue == []


@pytest.mark.parametrize("ref_date", [
    "2026-10-28",
    "2026-11-01",
    "2026-11-15",
    "2026-12-01",
    "2026-12-31",
    "2027-01-10",
    "2027-03-25",
    "2027-06-30",
], ids=[
    "boundary_oct_28",
    "boundary_nov_01",
    "boundary_nov_15",
    "boundary_dec_01",
    "boundary_dec_31",
    "boundary_jan_10",
    "boundary_mar_25",
    "boundary_jun_30",
])
def test_overdue_boundary_today_not_overdue_parametrized(setup_service, ref_date):
    """
    Tasks due on ref_date must not be counted as overdue.
    """
    s, owner, _, _, p = setup_service
    s.create_task(p["id"], owner["id"], f"Task on {ref_date}", due_date=ref_date)
    overdue = s.get_overdue_tasks(p["id"], owner["id"], as_of_date=ref_date)
    assert len(overdue) == 0


# =============================================================================
# 4. Task Statistics Tests (Passing + Failing)
# =============================================================================

def test_task_statistics_empty_project(setup_service):
    s, owner, _, _, p = setup_service
    stats = s.get_task_statistics(p["id"], owner["id"])
    assert stats == {
        "total": 0,
        "completed": 0,
        "pending": 0,
        "completion_percentage": 0.0
    }


def test_task_statistics_counts(setup_service):
    s, owner, _, _, p = setup_service
    t1 = s.create_task(p["id"], owner["id"], "T1")
    t2 = s.create_task(p["id"], owner["id"], "T2")
    t3 = s.create_task(p["id"], owner["id"], "T3")
    s.change_status(t1["id"], owner["id"], "in_progress")
    s.change_status(t2["id"], owner["id"], "done")

    stats = s.get_task_statistics(p["id"], owner["id"])
    assert stats["total"] == 3
    assert stats["completed"] == 1
    assert stats["pending"] == 2


def test_task_statistics_completion_percentage(setup_service):
    """
    Completion percentage should be (completed / total) * 100, e.g. 50.0 for 2/4.
    """
    s, owner, _, _, p = setup_service
    t1 = s.create_task(p["id"], owner["id"], "Task 1")
    t2 = s.create_task(p["id"], owner["id"], "Task 2")
    s.create_task(p["id"], owner["id"], "Task 3")
    s.create_task(p["id"], owner["id"], "Task 4")
    s.change_status(t1["id"], owner["id"], "done")
    s.change_status(t2["id"], owner["id"], "done")

    stats = s.get_task_statistics(p["id"], owner["id"])
    assert stats["completion_percentage"] == 50.0


@pytest.mark.parametrize("total_tasks,done_tasks,expected_pct", [
    (2, 1, 50.0),
    (4, 1, 25.0),
    (4, 3, 75.0),
    (5, 1, 20.0),
    (5, 2, 40.0),
    (5, 4, 80.0),
    (1, 1, 100.0),
    (10, 7, 70.0),
], ids=[
    "half_complete_50pct",
    "one_quarter_25pct",
    "three_quarters_75pct",
    "one_fifth_20pct",
    "two_fifths_40pct",
    "four_fifths_80pct",
    "all_complete_100pct",
    "seven_tenths_70pct",
])
def test_task_statistics_completion_percentage_parametrized(setup_service, total_tasks, done_tasks, expected_pct):
    """
    Completion percentage must be expressed as percentage out of 100, not fraction.
    """
    s, owner, _, _, p = setup_service
    tasks = [s.create_task(p["id"], owner["id"], f"Task {i}") for i in range(total_tasks)]
    for i in range(done_tasks):
        s.change_status(tasks[i]["id"], owner["id"], "done")

    stats = s.get_task_statistics(p["id"], owner["id"])
    assert stats["completion_percentage"] == expected_pct


# =============================================================================
# 5. Task Assignment Tests (Passing)
# =============================================================================

def test_assign_task_success(setup_service):
    s, owner, member, _, p = setup_service
    t = s.create_task(p["id"], owner["id"], "Task")
    updated = s.assign_task(t["id"], owner["id"], member["id"])
    assert updated["assignee_id"] == member["id"]


def test_assign_task_unauthorized_user_forbidden(setup_service):
    s, owner, member, outsider, p = setup_service
    t = s.create_task(p["id"], owner["id"], "Task")
    with pytest.raises(Forbidden):
        s.assign_task(t["id"], member["id"], outsider["id"])


def test_assign_task_unknown_user_rejected(setup_service):
    s, owner, _, _, p = setup_service
    t = s.create_task(p["id"], owner["id"], "Task")
    with pytest.raises(NotFound, match="assignee"):
        s.assign_task(t["id"], owner["id"], 8888)


# =============================================================================
# 6. Task Sorting and Pagination Tests (Passing)
# =============================================================================

def test_sort_tasks_by_priority(setup_service):
    s, owner, _, _, p = setup_service
    s.create_task(p["id"], owner["id"], "Low", priority=5)
    s.create_task(p["id"], owner["id"], "High", priority=1)
    s.create_task(p["id"], owner["id"], "Mid", priority=3)

    asc = s.get_sorted_tasks(p["id"], owner["id"], sort_by="priority", order="asc")
    assert [t["title"] for t in asc] == ["High", "Mid", "Low"]

    desc = s.get_sorted_tasks(p["id"], owner["id"], sort_by="priority", order="desc")
    assert [t["title"] for t in desc] == ["Low", "Mid", "High"]


def test_sort_tasks_by_due_date(setup_service):
    s, owner, _, _, p = setup_service
    s.create_task(p["id"], owner["id"], "Late", due_date="2026-12-01")
    s.create_task(p["id"], owner["id"], "Early", due_date="2026-10-15")
    s.create_task(p["id"], owner["id"], "No Due Date")

    results = s.get_sorted_tasks(p["id"], owner["id"], sort_by="due_date", order="asc")
    assert [t["title"] for t in results] == ["Early", "Late", "No Due Date"]


def test_sort_tasks_invalid_field_rejected(setup_service):
    s, owner, _, _, p = setup_service
    with pytest.raises(InvalidInput, match="sort field"):
        s.get_sorted_tasks(p["id"], owner["id"], sort_by="non_existent")


def test_sorted_tasks_pagination(setup_service):
    s, owner, _, _, p = setup_service
    for i in range(1, 6):
        s.create_task(p["id"], owner["id"], f"Task {i}", priority=i)

    page2 = s.get_sorted_tasks(
        p["id"], owner["id"],
        sort_by="priority", order="asc",
        offset=2, limit=2
    )
    assert [t["title"] for t in page2] == ["Task 3", "Task 4"]


# =============================================================================
# 7. Duplicate User Name Validation Tests (Failing)
# =============================================================================

@pytest.mark.parametrize("first_name,second_name", [
    ("Alice", "alice"),
    ("BOB", "bob"),
    ("Charlie", "CHARLIE"),
    ("David", "  David  "),
    ("EveDeveloper", "evedeveloper"),
    ("FrankTester", "franktester"),
    ("GraceAdmin", "graceadmin"),
    ("HenryManager", "henrymanager"),
], ids=[
    "dup_alice_lowercase",
    "dup_bob_uppercase_original",
    "dup_charlie_uppercase_duplicate",
    "dup_david_whitespace",
    "dup_eve_developer",
    "dup_frank_tester",
    "dup_grace_admin",
    "dup_henry_manager",
])
def test_duplicate_user_name_rejected_variations(setup_service, first_name, second_name):
    """
    Creating a user with an already taken name (case-insensitive) must raise InvalidInput.
    """
    s, _, _, _, _ = setup_service
    s.create_user(first_name)
    with pytest.raises(InvalidInput, match="already exists"):
        s.create_user(second_name)


# =============================================================================
# 8. Outsider Status Change Permission Tests (Failing)
# =============================================================================

@pytest.mark.parametrize("target_status,user_label", [
    ("in_progress", "guest1"),
    ("done", "guest2"),
    ("in_progress", "visitor1"),
    ("done", "visitor2"),
    ("in_progress", "auditor1"),
    ("done", "auditor2"),
], ids=[
    "outsider_guest1_to_in_progress",
    "outsider_guest2_to_done",
    "outsider_visitor1_to_in_progress",
    "outsider_visitor2_to_done",
    "outsider_auditor1_to_in_progress",
    "outsider_auditor2_to_done",
])
def test_outsider_cannot_change_status_variations(setup_service, target_status, user_label):
    """
    Users outside the project must be forbidden from updating task statuses.
    """
    s, owner, _, _, p = setup_service
    outsider_user = s.create_user(user_label)
    task = s.create_task(p["id"], owner["id"], f"Task for {user_label}")
    with pytest.raises(Forbidden):
        s.change_status(task["id"], outsider_user["id"], target_status)


# =============================================================================
# 9. Filter Before Pagination Tests (Failing)
# =============================================================================

@pytest.mark.parametrize("filter_priority,filter_status,expected_title", [
    (1, None, "Match Priority 1"),
    (2, None, "Match Priority 2"),
    (4, None, "Match Priority 4"),
    (5, None, "Match Priority 5"),
    (None, "done", "Match Status Done"),
    (None, "in_progress", "Match Status In Progress"),
    (1, "todo", "Match Priority 1 Todo"),
], ids=[
    "filter_p1_limit_1",
    "filter_p2_limit_1",
    "filter_p4_limit_1",
    "filter_p5_limit_1",
    "filter_status_done_limit_1",
    "filter_status_in_progress_limit_1",
    "filter_p1_status_todo_limit_1",
])
def test_filter_before_pagination_variations(setup_service, filter_priority, filter_status, expected_title):
    """
    Filtering must occur before pagination slicing [offset:offset+limit].
    """
    s, owner, _, _, p = setup_service
    # Create non-matching tasks first
    s.create_task(p["id"], owner["id"], "Noise Task 1", priority=3)
    s.create_task(p["id"], owner["id"], "Noise Task 2", priority=3)
    s.create_task(p["id"], owner["id"], "Noise Task 3", priority=3)

    # Create target matching task
    target_p = filter_priority if filter_priority is not None else 3
    t = s.create_task(p["id"], owner["id"], expected_title, priority=target_p)
    if filter_status == "done":
        s.change_status(t["id"], owner["id"], "done")
    elif filter_status == "in_progress":
        s.change_status(t["id"], owner["id"], "in_progress")

    results = s.list_tasks(
        p["id"], owner["id"],
        status=filter_status, priority=filter_priority,
        offset=0, limit=1
    )
    assert [item["title"] for item in results] == [expected_title]


# =============================================================================
# 10. API Integration Tests (Passing)
# =============================================================================

def test_api_task_search(client):
    user = client.post("/users", json={"name": "Alice"}).json()
    project = client.post(
        "/projects",
        json={"name": "Dev", "owner_id": user["id"]}
    ).json()
    client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "Refactor router", "actor_id": user["id"]}
    )

    resp = client.get(
        f"/projects/{project['id']}/tasks/search",
        params={"actor_id": user["id"], "query": "router"}
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["items"][0]["title"] == "Refactor router"


def test_api_task_assignment(client):
    owner = client.post("/users", json={"name": "OwnerBob"}).json()
    assignee = client.post("/users", json={"name": "DevCharlie"}).json()
    project = client.post(
        "/projects",
        json={"name": "App", "owner_id": owner["id"]}
    ).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "Write Docs", "actor_id": owner["id"]}
    ).json()

    resp = client.post(
        f"/tasks/{task['id']}/assign",
        json={"actor_id": owner["id"], "assignee_id": assignee["id"]}
    )
    assert resp.status_code == 200
    assert resp.json()["assignee_id"] == assignee["id"]


def test_api_task_statistics(client):
    user = client.post("/users", json={"name": "Manager"}).json()
    project = client.post(
        "/projects",
        json={"name": "Roadmap", "owner_id": user["id"]}
    ).json()
    client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "Feature 1", "actor_id": user["id"]}
    )

    resp = client.get(
        f"/projects/{project['id']}/statistics",
        params={"actor_id": user["id"]}
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["pending"] == 1
