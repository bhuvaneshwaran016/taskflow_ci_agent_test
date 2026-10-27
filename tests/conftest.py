import pytest
from fastapi.testclient import TestClient

from taskflow.store import Store
from taskflow.service import TaskFlowService
from taskflow import api


@pytest.fixture
def setup_service():
    store = Store()
    service = TaskFlowService(store)
    owner = service.create_user("Owner")
    member = service.create_user("Member")
    outsider = service.create_user("Outsider")
    project = service.create_project("Website", owner["id"])
    return service, owner, member, outsider, project


@pytest.fixture
def client():
    api.service = TaskFlowService(Store())
    return TestClient(api.app)
