import logging
from unittest.mock import MagicMock

from globus_sdk import ComputeAPIError

from diamond_backend.app.utils import data_prep


class FakeComputeAPIError(ComputeAPIError):
    def __init__(self, code="RESOURCE_CONFLICT", http_status=409, message="boom"):
        self.code = code
        self.http_status = http_status
        self.messages = [message]


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
