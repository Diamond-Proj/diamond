import itertools
from unittest.mock import MagicMock, patch

import pytest
from globus_compute_sdk.errors import TaskExecutionFailed, TaskPending

from diamond_backend.app import app


@pytest.fixture
def client(test_identity):
    app.config["TESTING"] = True
    with app.test_client() as client:
        client.set_cookie("primary_identity", test_identity)
        client.set_cookie("tokens", "TEST_TOKENS")
        yield client


@pytest.mark.parametrize(
    "get_result_error, status, code",
    [
        (TaskExecutionFailed(""), 502, "COMPUTE_TASK_FAILED"),
        (TaskPending("pending"), 504, "COMPUTE_TASK_TIMEOUT"),
    ],
)
def test_set_diamond_work_path_reports_compute_errors(
    client,
    caplog,
    test_db,
    test_identity,
    test_endpoint_anvil,
    get_result_error,
    status,
    code,
):
    endpoint_uuid = test_endpoint_anvil[2]
    saved_before = test_db.get_diamond_dir(test_identity, endpoint_uuid)
    compute_client = MagicMock()
    compute_client.register_function.return_value = "FUNC_ID"
    compute_client.batch_run.return_value = {"tasks": {"FUNC_ID": ["TASK_ID"]}}
    compute_client.get_result.side_effect = get_result_error

    with (
        patch(
            "diamond_backend.app.endpoints.initialize_globus_compute_client",
            return_value=compute_client,
        ),
        patch("diamond_backend.app.utils.compute.time.sleep"),
        # Every clock read is 100 s later, so the first pending poll is past
        # the deadline.
        patch(
            "diamond_backend.app.utils.compute.time.monotonic",
            side_effect=itertools.count(0.0, 100.0),
        ),
    ):
        response = client.post(
            "/api/set_diamond_work_path",
            json={"endpoint_uuid": endpoint_uuid, "diamond_work_path": "/u/username"},
        )

    assert response.status_code == status, response.get_data(as_text=True)
    body = response.get_json()
    assert body["code"] == code
    assert body["error_args"][:2] == ["TASK_ID", endpoint_uuid]
    # The directory-creation task is never submitted and nothing is saved.
    assert compute_client.batch_run.call_count == 1
    assert test_db.get_diamond_dir(test_identity, endpoint_uuid) == saved_before
    # Failure logs identify the endpoint and the user behind the task.
    endpoint_name = test_endpoint_anvil[0]
    email = test_db.load_profile(test_identity).email
    assert any(
        "TASK_ID" in message
        and endpoint_uuid in message
        and f"({endpoint_name})" in message
        and f"user {email}" in message
        for message in caplog.messages
    ), caplog.messages
