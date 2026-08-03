import logging
from unittest.mock import MagicMock

from globus_compute_sdk.errors import TaskPending
from globus_sdk import ComputeAPIError

from diamond_backend.app.utils import data_prep


class FakeComputeAPIError(ComputeAPIError):
    def __init__(self, code="RESOURCE_CONFLICT", http_status=409, message="boom"):
        self.code = code
        self.http_status = http_status
        self.messages = [message]


class DummyResult:
    def __init__(self, stdout: str):
        self.stdout = stdout


def test_wait_for_metadata_result_returns_after_pending(monkeypatch):
    client = MagicMock()
    result = DummyResult("payload")
    client.get_result.side_effect = [TaskPending("pending"), result]
    monkeypatch.setattr(data_prep.time, "sleep", lambda *_: None)

    returned = data_prep._wait_for_metadata_result(
        client,
        "TASK_ID",
        logging.getLogger("test"),
        max_attempts=3,
    )

    assert returned is result


def test_wait_for_metadata_result_times_out(monkeypatch):
    client = MagicMock()

    def _raise_pending(*_args, **_kwargs):
        raise TaskPending("pending")

    client.get_result.side_effect = _raise_pending
    monkeypatch.setattr(data_prep.time, "sleep", lambda *_: None)

    returned = data_prep._wait_for_metadata_result(
        client,
        "TASK_ID",
        logging.getLogger("test"),
        max_attempts=2,
    )

    assert returned is None


def test_submit_metadata_task_retries_on_conflict(monkeypatch):
    client = MagicMock()
    client.batch_run.side_effect = [
        FakeComputeAPIError(),
        {"tasks": {"FUNC_ID": ["TASK_ID"]}},
    ]
    monkeypatch.setattr(data_prep.time, "sleep", lambda *_: None)

    task_id = data_prep._submit_metadata_task_with_retry(
        "ENDPOINT_ID",
        client,
        "FUNC_ID",
        logging.getLogger("test"),
        max_attempts=2,
        user_endpoint_config=None,
    )

    assert task_id == "TASK_ID"


def test_submit_metadata_task_returns_none_on_non_retryable(monkeypatch):
    client = MagicMock()
    client.batch_run.side_effect = [
        FakeComputeAPIError(code="SEMANTICALLY_INVALID", http_status=422)
    ]
    monkeypatch.setattr(data_prep.time, "sleep", lambda *_: None)

    task_id = data_prep._submit_metadata_task_with_retry(
        "ENDPOINT_ID",
        client,
        "FUNC_ID",
        logging.getLogger("test"),
        max_attempts=1,
    )

    assert task_id is None
