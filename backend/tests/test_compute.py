import logging
from unittest.mock import MagicMock

import pytest
from globus_compute_sdk.errors import TaskExecutionFailed, TaskPending
from globus_sdk import ComputeAPIError

from diamond_backend.app.utils import compute
from diamond_backend.app.utils.errors import ComputeTaskFailed, ComputeTaskTimeout


class FakeComputeAPIError(ComputeAPIError):
    def __init__(self, code="UNAUTHORIZED", http_status=401, message="boom"):
        self.code = code
        self.http_status = http_status
        self.messages = [message]


class DummyResult:
    def __init__(self, stdout: str):
        self.stdout = stdout


class FakeClock:
    """Monotonic clock that advances only when the code under test sleeps."""

    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(compute.time, "monotonic", fake.monotonic)
    monkeypatch.setattr(compute.time, "sleep", fake.sleep)
    return fake


def test_wait_for_compute_result_returns_after_pending(clock, caplog):
    client = MagicMock()
    result = DummyResult("payload")
    client.get_result.side_effect = [TaskPending("pending"), result]

    with caplog.at_level(logging.INFO, logger="test"):
        returned = compute.wait_for_compute_result(
            client,
            "TASK_ID",
            "ENDPOINT_ID",
            logging.getLogger("test"),
            endpoint_name="Delta EP",
            username="user@example.edu",
        )

    assert returned is result
    assert clock.sleeps == [1.0]
    assert (
        "Compute task TASK_ID on endpoint ENDPOINT_ID (Delta EP), "
        "user user@example.edu returned after 1.0s." in caplog.messages
    )


def test_wait_for_compute_result_times_out_at_deadline(clock):
    client = MagicMock()
    client.get_result.side_effect = TaskPending("pending")

    with pytest.raises(ComputeTaskTimeout) as excinfo:
        compute.wait_for_compute_result(
            client, "TASK_ID", "ENDPOINT_ID", logging.getLogger("test"), timeout_s=10
        )

    assert excinfo.value.http_status_code == 504
    assert excinfo.value.error_args == ["TASK_ID", "ENDPOINT_ID"]
    # Never sleeps past the deadline.
    assert sum(clock.sleeps) == pytest.approx(10)


@pytest.mark.parametrize(
    "exc",
    [
        TaskExecutionFailed(""),
        FakeComputeAPIError(code="UNAUTHORIZED", http_status=401),
        ConnectionError("reset"),
    ],
)
def test_wait_for_compute_result_wraps_failures(clock, exc):
    client = MagicMock()
    client.get_result.side_effect = [TaskPending("pending"), exc]

    with pytest.raises(ComputeTaskFailed) as excinfo:
        compute.wait_for_compute_result(
            client, "TASK_ID", "ENDPOINT_ID", logging.getLogger("test")
        )

    assert excinfo.value.http_status_code == 502
    assert excinfo.value.error_args == ["TASK_ID", "ENDPOINT_ID", type(exc).__name__]
    assert excinfo.value.__cause__ is exc
