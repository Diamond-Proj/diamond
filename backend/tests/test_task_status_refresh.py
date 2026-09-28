"""Regression guard for the Globus Compute call volume of the task-status poll.

The task list is polled every 10s by three separate frontend components, all of
which land in refresh_identity_task_statuses. Constructing a Globus Compute
client performs a blocking version-check HTTP round trip, so building one when
there is nothing to refresh is pure waste repeated six times a minute per
component.
"""

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest

from diamond_backend.app import app, g_database, g_runtime_redis
from diamond_backend.app.task_runtime import (
    GET_TASK_STATUS_DTASK_TYPE,
    _endpoint_breaker_key,
    refresh_identity_task_statuses,
)

TEST_IDENTITY = "TEST_IDENTITY_1"


@pytest.fixture
def clean_runtime_cache(test_endpoint_anvil):
    """g_runtime_redis is a process-global dict; keep tests independent."""
    keys = [
        f"dtask:{TEST_IDENTITY}:{GET_TASK_STATUS_DTASK_TYPE}",
        _endpoint_breaker_key(test_endpoint_anvil[2]),
    ]
    for key in keys:
        g_runtime_redis.delete(key)
    yield
    for key in keys:
        g_runtime_redis.delete(key)


@pytest.fixture
def seeded_tasks(test_db, test_endpoint_anvil):
    """Create tasks for this test and remove them afterwards."""
    created = []

    def _create(task_status):
        task_id = str(uuid.uuid4())
        with app.app_context():
            g_database.save_task(
                task_id=task_id,
                batch_job_id="12345678",
                task_name=f"task-{task_status}",
                identity_id=TEST_IDENTITY,
                task_status=task_status,
                task_create_time=datetime.now(),
                log_path=None,
                stdout_path=None,
                stderr_path=None,
                compute_endpoint_id=test_endpoint_anvil[2],
                checkpoint_path=None,
            )
        created.append(task_id)
        return task_id

    yield _create

    with app.app_context():
        for task_id in created:
            g_database.delete_task(task_id)


@pytest.mark.parametrize("terminal_status", ["COMPLETED", "FAILED", "MISSING"])
def test_no_compute_client_when_every_task_is_terminal(
    clean_runtime_cache, seeded_tasks, terminal_status
):
    """The fix: a finished task list must cost zero Globus Compute calls.

    Before this guard, every poll built a client -- and Client.__init__ performs
    a version-check HTTP request -- only for _queue_task_status_refreshes to
    filter the list to empty and return without making any call of its own.
    """
    seeded_tasks(terminal_status)

    with patch(
        "diamond_backend.app.task_runtime.initialize_globus_compute_client"
    ) as mock_client:
        with app.app_context():
            tasks = refresh_identity_task_statuses(TEST_IDENTITY)

    assert mock_client.call_count == 0
    assert any(task.task_status == terminal_status for task in tasks)


def test_compute_client_still_built_when_a_task_is_active(
    clean_runtime_cache, seeded_tasks
):
    """The early return must not suppress refreshes that are still needed."""
    seeded_tasks("COMPLETED")
    seeded_tasks("RUNNING")

    with patch(
        "diamond_backend.app.task_runtime.initialize_globus_compute_client"
    ) as mock_client:
        with patch(
            "diamond_backend.app.task_runtime._queue_task_status_refreshes",
            return_value=[],
        ) as mock_queue:
            with app.app_context():
                refresh_identity_task_statuses(TEST_IDENTITY)

    assert mock_client.call_count == 1
    assert mock_queue.call_count == 1


def test_submit_failure_trips_breaker_and_it_expires(
    clean_runtime_cache, seeded_tasks, test_endpoint_anvil
):
    """A failing endpoint is suppressed, then retried once the cooldown lapses.

    Without the breaker, a down endpoint means every poll re-submits and fails
    again -- the submit storm this exists to stop.
    """
    endpoint_uuid = test_endpoint_anvil[2]
    seeded_tasks("RUNNING")

    with patch(
        "diamond_backend.app.task_runtime.initialize_globus_compute_client"
    ) as mock_client:
        with patch(
            "diamond_backend.app.task_runtime.globus_compute_wrapped_run",
            side_effect=Exception("endpoint offline"),
        ) as mock_submit:
            with app.app_context():
                refresh_identity_task_statuses(TEST_IDENTITY)
            assert mock_submit.call_count == 1
            assert g_runtime_redis.exists(_endpoint_breaker_key(endpoint_uuid))

            # While tripped: no client, no submit -- the poll costs nothing.
            mock_client.reset_mock()
            with app.app_context():
                refresh_identity_task_statuses(TEST_IDENTITY)
            assert mock_client.call_count == 0
            assert mock_submit.call_count == 1

            # Once the cooldown lapses we try again: self-healing, no operator step.
            g_runtime_redis.delete(_endpoint_breaker_key(endpoint_uuid))
            with app.app_context():
                refresh_identity_task_statuses(TEST_IDENTITY)
            assert mock_submit.call_count == 2


def test_breaker_short_circuits_remaining_tasks_on_same_endpoint(
    clean_runtime_cache, seeded_tasks
):
    """One failure suppresses the rest of that endpoint's tasks in the same pass."""
    for _ in range(4):
        seeded_tasks("RUNNING")

    with patch("diamond_backend.app.task_runtime.initialize_globus_compute_client"):
        with patch(
            "diamond_backend.app.task_runtime.globus_compute_wrapped_run",
            side_effect=Exception("endpoint offline"),
        ) as mock_submit:
            with app.app_context():
                refresh_identity_task_statuses(TEST_IDENTITY)

    assert mock_submit.call_count == 1


def test_returns_all_tasks_including_terminal_ones(clean_runtime_cache, seeded_tasks):
    """The early return must not change what callers receive.

    tasks.py, containers.py and images.py all render from this list, so a
    terminal task disappearing here would blank the UI.
    """
    completed_id = seeded_tasks("COMPLETED")

    with patch("diamond_backend.app.task_runtime.initialize_globus_compute_client"):
        with app.app_context():
            tasks = refresh_identity_task_statuses(TEST_IDENTITY)

    assert completed_id in {task.task_id for task in tasks}
