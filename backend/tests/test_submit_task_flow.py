"""Coverage for the Globus Flows-backed /api/submit_task and /api/get_task_status path.

submit_flow and get_flow_result are mocked throughout: these tests are about the
contract between tasks.py and flows.py (response shapes, status transitions), not
about the real Globus Flows/Compute services.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from flask import jsonify

from diamond_backend.app import g_database, g_runtime_redis
from diamond_backend.app.database.db import db
from diamond_backend.app.database.models.function import Functions
from diamond_backend.app.tasks import GET_TASK_STATUS_DTASK_TYPE

SUBMIT_SLURM_JOB_FUNCTION_ID = "FAKE-SUBMIT-SLURM-JOB-FUNCTION-ID"


def _set_submit_slurm_job_function(function_id):
    """Seed (or remove) the submit_slurm_job Functions row deterministically.

    check_and_create_functions() only populates this row when it can reach a
    real Globus Compute service, which it can't in tests, so each test must
    put the row in the state it needs rather than rely on leftover state.
    """
    Functions.query.filter_by(name="submit_slurm_job").delete()
    if function_id is not None:
        db.session.add(Functions(name="submit_slurm_job", function_id=function_id))
    db.session.commit()


def _submit_task_body(*, endpoint_uuid, task_name):
    return {
        "endpoint": endpoint_uuid,
        "taskName": task_name,
        "partition": "gpu",
        "account": "proj",
        "container": "TestContainer1",
        "time_duration": "00:10:00",
        "task": "echo hello",
    }


@pytest.fixture(autouse=True)
def _diamond_dir(monkeypatch):
    monkeypatch.setattr(
        g_database,
        "get_diamond_dir",
        lambda endpoint_uuid, identity_id: "/tmp/diamond",
    )


def test_submit_task_success_saves_submitting_task(
    client, monkeypatch, test_endpoint_anvil
):
    _set_submit_slurm_job_function(SUBMIT_SLURM_JOB_FUNCTION_ID)
    flow_run_id = f"FLOW-RUN-{uuid4().hex[:8]}"

    def fake_submit_flow(request_json, request_cookies, function_id, fn_params):
        assert function_id == SUBMIT_SLURM_JOB_FUNCTION_ID
        assert "submit_task_script" in fn_params
        return jsonify({"flow_run_id": flow_run_id, "flow_id": "FLOW-1"}), 200

    monkeypatch.setattr("diamond_backend.app.tasks.submit_flow", fake_submit_flow)

    response = client.post(
        "/api/submit_task",
        json=_submit_task_body(
            endpoint_uuid=test_endpoint_anvil[2],
            task_name=f"submit-task-{uuid4().hex[:8]}",
        ),
    )

    assert response.status_code == 200
    assert response.get_json()["flow_run_id"] == flow_run_id

    task = g_database.get_task(task_id=flow_run_id)
    assert task is not None
    assert task.task_status == "SUBMITTING"

    g_database.delete_task(flow_run_id)


def test_submit_task_forwards_non_200_error_tuple(
    client, monkeypatch, test_endpoint_anvil
):
    # submit_flow can fail with a (response, status) tuple, e.g. a Globus API
    # error. The route must forward it as-is instead of calling result.json
    # on a tuple.
    _set_submit_slurm_job_function(SUBMIT_SLURM_JOB_FUNCTION_ID)

    def fake_submit_flow(request_json, request_cookies, function_id, fn_params):
        return jsonify({"error": "boom", "messages": ["m1"], "code": 403}), 403

    monkeypatch.setattr("diamond_backend.app.tasks.submit_flow", fake_submit_flow)

    response = client.post(
        "/api/submit_task",
        json=_submit_task_body(
            endpoint_uuid=test_endpoint_anvil[2],
            task_name=f"submit-task-{uuid4().hex[:8]}",
        ),
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "boom"


def test_submit_task_missing_flow_run_id_returns_error(
    client, monkeypatch, test_endpoint_anvil
):
    # A 200 response with no flow_run_id (e.g. the flow row was missing) must
    # not be treated as success: no task row should be created with
    # task_id=None, and the route must report an error.
    _set_submit_slurm_job_function(SUBMIT_SLURM_JOB_FUNCTION_ID)

    def fake_submit_flow(request_json, request_cookies, function_id, fn_params):
        return jsonify({"flow_id": "FLOW-1"}), 200

    monkeypatch.setattr("diamond_backend.app.tasks.submit_flow", fake_submit_flow)

    response = client.post(
        "/api/submit_task",
        json=_submit_task_body(
            endpoint_uuid=test_endpoint_anvil[2],
            task_name=f"submit-task-{uuid4().hex[:8]}",
        ),
    )

    assert response.status_code == 500
    assert "error" in response.get_json()
    assert g_database.get_task(task_id=None) is None


def test_submit_task_missing_registered_function_returns_error(
    client, test_endpoint_anvil
):
    # If submit_slurm_job was never registered (e.g. startup registration
    # failed), the route must report a clean error instead of raising
    # AttributeError on None.function_id.
    _set_submit_slurm_job_function(None)

    response = client.post(
        "/api/submit_task",
        json=_submit_task_body(
            endpoint_uuid=test_endpoint_anvil[2],
            task_name=f"submit-task-{uuid4().hex[:8]}",
        ),
    )

    assert response.status_code == 500
    assert "error" in response.get_json()


def _prime_task_status_redis_cache(test_identity):
    # The SUBMITTING/ACTIVE task refresh only runs on a warm dtask cache
    # (see diamond_get_task_status), so seed an empty pending-record list to
    # reach it deterministically.
    redis_key = f"dtask:{test_identity}:{GET_TASK_STATUS_DTASK_TYPE}"
    g_runtime_redis.set(redis_key, [], ttl_seconds=30)


@pytest.fixture(autouse=True)
def _mock_compute_client(monkeypatch):
    from unittest.mock import MagicMock

    monkeypatch.setattr(
        "diamond_backend.app.tasks.initialize_globus_compute_client",
        lambda: MagicMock(),
    )


def test_get_task_status_marks_failed_flow_as_failed(
    client, test_identity, test_endpoint_anvil, monkeypatch
):
    task_id = f"FLOW-RUN-{uuid4().hex[:8]}"
    g_database.save_task(
        task_id=task_id,
        batch_job_id="",
        task_name="failed-flow-task",
        identity_id=test_identity,
        task_status="SUBMITTING",
        task_create_time=datetime.now(),
        log_path="",
        stdout_path="/tmp/diamond/logs/failed.stdout",
        stderr_path="/tmp/diamond/logs/failed.stderr",
        compute_endpoint_id=test_endpoint_anvil[2],
        checkpoint_path="",
    )
    _prime_task_status_redis_cache(test_identity)

    monkeypatch.setattr(
        "diamond_backend.app.tasks.get_flow_result",
        lambda request_cookies, flow_run_id: {
            "status": "FAILED",
            "details": {"error": "sbatch exited non-zero"},
        },
    )

    try:
        response = client.get("/api/get_task_status")
        assert response.status_code == 200
        task = g_database.get_task(task_id=task_id)
        assert task.task_status == "FAILED"
    finally:
        g_database.delete_task(task_id)


def test_get_task_status_marks_inactive_flow_as_failed(
    client, test_identity, test_endpoint_anvil, monkeypatch
):
    task_id = f"FLOW-RUN-{uuid4().hex[:8]}"
    g_database.save_task(
        task_id=task_id,
        batch_job_id="",
        task_name="inactive-flow-task",
        identity_id=test_identity,
        task_status="SUBMITTING",
        task_create_time=datetime.now(),
        log_path="",
        stdout_path="/tmp/diamond/logs/inactive.stdout",
        stderr_path="/tmp/diamond/logs/inactive.stderr",
        compute_endpoint_id=test_endpoint_anvil[2],
        checkpoint_path="",
    )
    _prime_task_status_redis_cache(test_identity)

    monkeypatch.setattr(
        "diamond_backend.app.tasks.get_flow_result",
        lambda request_cookies, flow_run_id: {
            "status": "INACTIVE",
            "details": {"reason": "consent required"},
        },
    )

    try:
        response = client.get("/api/get_task_status")
        assert response.status_code == 200
        task = g_database.get_task(task_id=task_id)
        assert task.task_status == "FAILED"
    finally:
        g_database.delete_task(task_id)


def test_get_task_status_marks_succeeded_flow_active_with_job_id(
    client, test_identity, test_endpoint_anvil, monkeypatch
):
    task_id = f"FLOW-RUN-{uuid4().hex[:8]}"
    g_database.save_task(
        task_id=task_id,
        batch_job_id="",
        task_name="succeeded-flow-task",
        identity_id=test_identity,
        task_status="SUBMITTING",
        task_create_time=datetime.now(),
        log_path="",
        stdout_path="/tmp/diamond/logs/succeeded.stdout",
        stderr_path="/tmp/diamond/logs/succeeded.stderr",
        compute_endpoint_id=test_endpoint_anvil[2],
        checkpoint_path="",
    )
    _prime_task_status_redis_cache(test_identity)

    artifact_path = "/work/nvme/bcrc/hxie6/demo-sft"
    monkeypatch.setattr(
        "diamond_backend.app.tasks.get_flow_result",
        lambda request_cookies, flow_run_id: {
            "status": "SUCCEEDED",
            "details": {
                "output": {
                    "run_function": {
                        "details": {
                            "result": [
                                "Submitted batch job 987654\n"
                                f"DIAMOND_ARTIFACT_PATH={artifact_path}"
                            ]
                        }
                    }
                }
            },
        },
    )

    new_task_id = "987654"
    try:
        response = client.get("/api/get_task_status")
        assert response.status_code == 200
        task = g_database.get_task(task_id=new_task_id)
        assert task is not None
        assert task.task_status == "ACTIVE"
        assert task.batch_job_id == new_task_id
        # The real (script-produced) artifact path replaces the pre-submission guess.
        assert task.checkpoint_path == artifact_path
    finally:
        g_database.delete_task(new_task_id)


def test_get_task_status_succeeded_flow_without_job_id_marks_failed(
    client, test_identity, test_endpoint_anvil, monkeypatch
):
    # If sbatch's own output doesn't contain a parseable job ID, the task
    # must not be silently left as SUBMITTING forever.
    task_id = f"FLOW-RUN-{uuid4().hex[:8]}"
    g_database.save_task(
        task_id=task_id,
        batch_job_id="",
        task_name="succeeded-no-job-id-task",
        identity_id=test_identity,
        task_status="SUBMITTING",
        task_create_time=datetime.now(),
        log_path="",
        stdout_path="/tmp/diamond/logs/no-job-id.stdout",
        stderr_path="/tmp/diamond/logs/no-job-id.stderr",
        compute_endpoint_id=test_endpoint_anvil[2],
        checkpoint_path="",
    )
    _prime_task_status_redis_cache(test_identity)

    monkeypatch.setattr(
        "diamond_backend.app.tasks.get_flow_result",
        lambda request_cookies, flow_run_id: {
            "status": "SUCCEEDED",
            "details": {
                "output": {
                    "run_function": {"details": {"result": ["sbatch: error: ..."]}}
                }
            },
        },
    )

    try:
        response = client.get("/api/get_task_status")
        assert response.status_code == 200
        task = g_database.get_task(task_id=task_id)
        assert task.task_status == "FAILED"
    finally:
        g_database.delete_task(task_id)
