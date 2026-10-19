from unittest.mock import MagicMock, patch

import pytest

from diamond_backend.app import task_runtime
from diamond_backend.app.utils.errors import ComputeTaskFailed, ComputeTaskTimeout


def _wait():
    return task_runtime._wait_for_compute_result(
        MagicMock(),
        "TASK_ID",
        endpoint_id="EP_ID",
        endpoint_name="EP name",
        username="u@x.edu",
    )


def test_wait_returns_result_and_passes_owner_to_logs():
    with patch.object(
        task_runtime, "wait_for_compute_result", return_value="RESULT"
    ) as wait:
        assert _wait() == "RESULT"

    assert wait.call_args.kwargs == {"endpoint_name": "EP name", "username": "u@x.edu"}


def test_wait_timeout_keeps_job_submission_error():
    with patch.object(
        task_runtime,
        "wait_for_compute_result",
        side_effect=ComputeTaskTimeout("TASK_ID", "EP_ID", 66),
    ):
        with pytest.raises(task_runtime.TaskSubmissionError) as excinfo:
            _wait()

    assert excinfo.value.http_status == 500
    assert excinfo.value.to_response_payload() == {
        "error": "Failed to submit job - task timed out after maximum attempts",
        "task_id": "TASK_ID",
    }


def test_wait_failure_keeps_job_submission_error():
    remote = RuntimeError("remote traceback")
    failed = ComputeTaskFailed("TASK_ID", "EP_ID", remote)
    failed.__cause__ = remote
    with patch.object(task_runtime, "wait_for_compute_result", side_effect=failed):
        with pytest.raises(task_runtime.TaskSubmissionError) as excinfo:
            _wait()

    assert excinfo.value.http_status == 500
    assert excinfo.value.to_response_payload() == {
        "error": "Failed to submit job - could not fetch results from endpoint",
        "task_id": "TASK_ID",
        "details": "remote traceback",
    }
