# TaskFlow CI_Agent Evaluation Project

A deliberately buggy task-management API for evaluating automated bug repair.

Features include user creation, projects, task assignment, status transitions,
permissions, filtering, pagination, API validation, pytest and GitHub Actions.

Run locally:
    py -m pip install -r requirements.txt
    py -m pytest -v

Docker is included for reproducible test runs:
    docker build -t taskflow-ci-test .
    docker run --rm taskflow-ci-test

The first CI run is expected to fail. Fix application code; do not weaken tests.
