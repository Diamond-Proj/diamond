import logging
import os
import re
import time
from datetime import datetime

from globus_compute_sdk.errors import TaskPending

from diamond_backend.app import g_database, g_runtime_redis
from diamond_backend.app.utils.data_prep import globus_compute_wrapped_run
from diamond_backend.app.utils.functions import (
    _escape_shell_braces,
    _make_shell_function,
    fetch_task_status,
    get_task_log,
    list_directory_entries,
    read_file_base64,
    stage_base64_file,
)
from diamond_backend.app.utils.login_flow import initialize_globus_compute_client
from diamond_backend.app.utils.task_status import is_stale, is_terminal

logger = logging.getLogger(__name__)

GET_TASK_STATUS_DTASK_TYPE = "fetch_task_status"
GET_TASK_STATUS_REDIS_TTL_SECONDS = 30
SBATCH_JOB_ID_PATTERN = re.compile(r"Submitted batch job (\d+)")

# Cooldown before retrying an endpoint whose status submit failed. Kept short
# because the breaker is the only thing that notices an endpoint coming back:
# a longer cooldown means a longer frozen UI after recovery.
ENDPOINT_DOWN_TTL_SECONDS = max(30, int(os.getenv("ENDPOINT_DOWN_TTL_SECONDS", "60")))

SLURM_STATE_MAPPING = {
    "COMPLETING": "COMPLETED",
    "COMPLETED+": "COMPLETED",
    "COMPLETED": "COMPLETED",
    "CANCELED": "COMPLETED",
    "FAILED": "FAILED",
    "TIMEOUT": "FAILED",
    "OUT_OF_MEMORY": "FAILED",
    "RUNNING": "RUNNING",
    "PENDING": "PENDING",
}


class TaskSubmissionError(Exception):
    def __init__(self, error, *, http_status=500, payload=None):
        super().__init__(error)
        self.error = error
        self.http_status = http_status
        self.payload = payload or {}

    def to_response_payload(self):
        return {"error": self.error, **self.payload}


def _wait_for_compute_result(globus_compute_client, task_id, *, max_attempts=12):
    compute_result = None
    for attempt in range(max_attempts):
        try:
            compute_result = globus_compute_client.get_result(task_id)
        except TaskPending:
            time.sleep(attempt)
            continue
        except Exception as exc:
            logger.exception("Failed to fetch results for task_id: %s", task_id)
            raise TaskSubmissionError(
                "Failed to submit job - could not fetch results from endpoint",
                payload={"task_id": task_id, "details": str(exc)},
            ) from exc
        else:
            break

    if compute_result is None:
        raise TaskSubmissionError(
            "Failed to submit job - task timed out after maximum attempts",
            payload={"task_id": task_id},
        )

    return compute_result


def _extract_slurm_batch_job_id(submit_result):
    submit_stdout = getattr(submit_result, "stdout", "")
    submit_stderr = getattr(submit_result, "stderr", "")
    submit_returncode = getattr(submit_result, "returncode", None)

    if submit_returncode not in (None, 0):
        error_message = "Failed to submit job - sbatch returned a non-zero exit code"
        if submit_stderr:
            error_message = f"{error_message}: {submit_stderr}"
        logger.error(
            "Submit task failed with return code %s. stdout=%s stderr=%s",
            submit_returncode,
            submit_stdout,
            submit_stderr,
        )
        raise TaskSubmissionError(
            error_message,
            payload={
                "stdout": submit_stdout,
                "stderr": submit_stderr,
                "returncode": submit_returncode,
            },
        )

    match = SBATCH_JOB_ID_PATTERN.search(submit_stdout)
    if not match:
        error_message = (
            "Failed to submit job - could not parse job ID from SLURM output"
        )
        if submit_stderr:
            error_message = f"{error_message}: {submit_stderr}"
        logger.error(
            "Could not parse job ID from stdout: %s stderr: %s",
            submit_stdout,
            submit_stderr,
        )
        raise TaskSubmissionError(
            error_message,
            payload={
                "stdout": submit_stdout,
                "stderr": submit_stderr,
                "returncode": submit_returncode,
            },
        )

    return match.group(1)


def run_endpoint_python_function(
    func,
    *,
    endpoint_id,
    identity_id,
    kwargs,
    error_message,
):
    """Run a registered Python function on the endpoint and wait for its result.

    Unlike shell functions, kwargs and results travel over the Globus Compute
    data plane, so payloads are not constrained by the kernel's command-line
    argument size limit.
    """
    globus_compute_client = initialize_globus_compute_client()
    user_endpoint_config = g_database.get_endpoint_user_config(
        identity_id=identity_id, endpoint_uuid=endpoint_id
    )
    function_id = globus_compute_client.register_function(func)

    try:
        task_id = globus_compute_wrapped_run(
            globus_compute_client,
            endpoint_id=endpoint_id,
            function_id=function_id,
            user_endpoint_config=user_endpoint_config,
            kwargs=kwargs,
        )
    except Exception as exc:
        logger.exception("Failed to submit %s task to Globus Compute", func.__name__)
        raise TaskSubmissionError(
            error_message,
            payload={"details": str(exc)},
        ) from exc

    try:
        return _wait_for_compute_result(globus_compute_client, task_id)
    except TaskSubmissionError as exc:
        raise TaskSubmissionError(
            error_message,
            http_status=exc.http_status,
            payload=exc.payload,
        ) from exc


def stage_base64_file_on_endpoint(
    *,
    endpoint_id,
    identity_id,
    file_path,
    content_b64,
):
    """Write a base64 payload to a file on the endpoint before job submission."""
    return run_endpoint_python_function(
        stage_base64_file,
        endpoint_id=endpoint_id,
        identity_id=identity_id,
        kwargs={"file_path": file_path, "content_b64": content_b64},
        error_message="Failed to upload file to endpoint",
    )


def list_endpoint_directory(*, endpoint_id, identity_id, dir_path):
    """List a directory on the endpoint (e.g. a task's artifact directory)."""
    return run_endpoint_python_function(
        list_directory_entries,
        endpoint_id=endpoint_id,
        identity_id=identity_id,
        kwargs={"dir_path": dir_path},
        error_message="Failed to list directory on endpoint",
    )


def read_endpoint_file_b64(*, endpoint_id, identity_id, artifact_path, filename):
    """Read one artifact file on the endpoint, returned base64-encoded."""
    return run_endpoint_python_function(
        read_file_base64,
        endpoint_id=endpoint_id,
        identity_id=identity_id,
        kwargs={"artifact_path": artifact_path, "filename": filename},
        error_message="Failed to read file from endpoint",
    )


def submit_batch_script_task(
    *,
    endpoint_id,
    identity_id,
    task_name,
    submit_script,
    stdout_path,
    stderr_path,
    log_path="",
    checkpoint_path="",
    checkpoint_path_extractor=None,
):
    globus_compute_client = initialize_globus_compute_client()
    user_endpoint_config = g_database.get_endpoint_user_config(
        identity_id=identity_id, endpoint_uuid=endpoint_id
    )

    submit_task_shell = _make_shell_function(_escape_shell_braces(submit_script))
    function_id = globus_compute_client.register_function(submit_task_shell)

    try:
        task_id = globus_compute_wrapped_run(
            globus_compute_client,
            endpoint_id=endpoint_id,
            function_id=function_id,
            user_endpoint_config=user_endpoint_config,
        )
    except Exception as exc:
        logger.exception("Failed to submit task to Globus Compute")
        http_status = getattr(exc, "http_status", 500)
        payload = {"details": str(exc)}
        messages = getattr(exc, "messages", None)
        if messages is not None:
            payload["messages"] = messages
        raise TaskSubmissionError(
            "Failed to submit task to Globus Compute",
            http_status=http_status,
            payload=payload,
        ) from exc

    submit_result = _wait_for_compute_result(globus_compute_client, task_id)
    if callable(checkpoint_path_extractor):
        extracted_checkpoint_path = checkpoint_path_extractor(
            getattr(submit_result, "stdout", "")
        )
        if extracted_checkpoint_path:
            checkpoint_path = extracted_checkpoint_path

    batch_job_id = _extract_slurm_batch_job_id(submit_result)
    logger.info("Task:%s is mapped to SLURM job ID:%s", task_id, batch_job_id)

    g_database.save_task(
        task_id=task_id,
        batch_job_id=batch_job_id,
        task_name=task_name,
        identity_id=identity_id,
        task_status="PENDING",
        task_create_time=datetime.now(),
        log_path=log_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        compute_endpoint_id=endpoint_id,
        checkpoint_path=checkpoint_path,
    )

    return {
        "task_id": task_id,
        "batch_job_id": batch_job_id,
        "task_name": task_name,
        "stdout_path": stdout_path,
        "stderr_path": stderr_path,
        "artifact_path": checkpoint_path,
    }


def _endpoint_breaker_key(endpoint_id):
    return f"epstate:down:{endpoint_id}"


def _endpoint_is_pollable(endpoint_id):
    """Whether we should submit a status probe to this endpoint right now.

    Evidence-based on purpose: the breaker trips only when a submit actually
    fails, and self-heals when the key expires. It deliberately does not consult
    Endpoints.endpoint_status, which is only written by an explicit
    POST /api/register_all_endpoints -- a stale "offline" there would suppress a
    healthy endpoint with nothing to ever clear it.
    """
    if not endpoint_id:
        return False
    return not g_runtime_redis.exists(_endpoint_breaker_key(endpoint_id))


def _trip_endpoint_breaker(endpoint_id):
    g_runtime_redis.set(
        _endpoint_breaker_key(endpoint_id),
        True,
        ttl_seconds=ENDPOINT_DOWN_TTL_SECONDS,
    )


def refreshable_tasks(tasks):
    """Tasks worth a Globus Compute round trip right now."""
    return [
        task
        for task in tasks
        if not is_terminal(task.task_status)
        and not is_stale(task)
        and _endpoint_is_pollable(task.compute_endpoint_id)
    ]


def _queue_task_status_refreshes(globus_compute_client, identity_id, tasks):
    filtered_tasks = refreshable_tasks(tasks)
    if not filtered_tasks:
        return []

    task_status_func_id = globus_compute_client.register_function(fetch_task_status)
    task_records = []
    for task in filtered_tasks:
        # Re-checked per task: a failure earlier in this loop trips the breaker,
        # so the rest of that endpoint's tasks skip their doomed submit.
        if not _endpoint_is_pollable(task.compute_endpoint_id):
            continue

        user_endpoint_config = g_database.get_endpoint_user_config(
            identity_id=identity_id, endpoint_uuid=task.compute_endpoint_id
        )
        try:
            task_status_task_id = globus_compute_wrapped_run(
                globus_compute_client,
                endpoint_id=task.compute_endpoint_id,
                function_id=task_status_func_id,
                user_endpoint_config=user_endpoint_config,
                kwargs={"batch_job_id": task.batch_job_id},
            )
        except Exception as exc:
            _trip_endpoint_breaker(task.compute_endpoint_id)
            logger.warning(
                "Failed to submit fetch_task_status for task %s; pausing endpoint "
                "%s for %ss. Error: %s",
                task.task_id,
                task.compute_endpoint_id,
                ENDPOINT_DOWN_TTL_SECONDS,
                exc,
            )
            continue

        task_records.append(
            {
                "identity_id": identity_id,
                "dtask_type": GET_TASK_STATUS_DTASK_TYPE,
                "task_id": task.task_id,
                "task_status_task_id": task_status_task_id,
            }
        )

    return task_records


def _apply_task_status_refreshes(globus_compute_client, runtime_record):
    pending_task_records = []
    for task_record in runtime_record:
        task_status_task_id = task_record["task_status_task_id"]
        try:
            task_status_task = globus_compute_client.get_task(task_status_task_id)
        except Exception as exc:
            logger.warning(
                "Failed to load task status task %s. Error: %s",
                task_status_task_id,
                exc,
            )
            continue

        if task_status_task.get("pending", False):
            pending_task_records.append(task_record)
            continue

        try:
            task_status_result = globus_compute_client.get_result(task_status_task_id)
        except Exception as exc:
            logger.warning(
                "Failed to fetch result for task status task %s. Error: %s",
                task_status_task_id,
                exc,
            )
            continue

        task_status = getattr(task_status_result, "stdout", "").strip()
        new_task_status = None
        if task_status:
            new_task_status = SLURM_STATE_MAPPING.get(task_status, "MISSING")
            if new_task_status == "MISSING":
                logger.warning(
                    "Unknown task status %s for task %s",
                    task_status,
                    task_record["task_id"],
                )
        else:
            try:
                previous_task_status = g_database.get_task_status(
                    task_record["task_id"]
                )
            except AttributeError:
                logger.warning("Task:%s removed", task_record["task_id"])
                continue
            if previous_task_status in ["RUNNING", "COMPLETING"]:
                new_task_status = "COMPLETED"

        if not new_task_status:
            continue

        try:
            g_database.update_task_status(task_record["task_id"], new_task_status)
            logger.info(
                "Updating Task:%s to %s",
                task_record["task_id"],
                new_task_status,
            )
        except Exception:
            logger.exception("Failed to update task:%s", task_record["task_id"])

    return pending_task_records


def refresh_identity_task_statuses(identity_id):
    redis_key = f"dtask:{identity_id}:{GET_TASK_STATUS_DTASK_TYPE}"
    runtime_record = g_runtime_redis.get(redis_key)

    if runtime_record is None:
        tasks = g_database.load_tasks(identity_id=identity_id)
        # Build the client only when something needs refreshing: Client.__init__
        # makes a blocking version-check HTTP call, and this runs on a 10s poll.
        if not refreshable_tasks(tasks):
            return tasks

        globus_compute_client = initialize_globus_compute_client()
        task_records = _queue_task_status_refreshes(
            globus_compute_client, identity_id, tasks
        )
        if task_records:
            g_runtime_redis.set(
                redis_key,
                task_records,
                ttl_seconds=GET_TASK_STATUS_REDIS_TTL_SECONDS,
            )
    else:
        globus_compute_client = initialize_globus_compute_client()
        pending_task_records = _apply_task_status_refreshes(
            globus_compute_client, runtime_record
        )
        if pending_task_records:
            g_runtime_redis.set(
                redis_key,
                pending_task_records,
                ttl_seconds=GET_TASK_STATUS_REDIS_TTL_SECONDS,
            )
        else:
            g_runtime_redis.delete(redis_key)

    return g_database.load_tasks(identity_id=identity_id)


def read_remote_task_log(
    *,
    identity_id,
    endpoint_id,
    log_path,
    max_attempts=5,
    retry_sleep_seconds=2,
):
    if not log_path:
        return {"content": "", "is_complete": False}

    globus_compute_client = initialize_globus_compute_client()
    get_task_log_func_id = globus_compute_client.register_function(get_task_log)
    user_endpoint_config = g_database.get_endpoint_user_config(
        identity_id=identity_id, endpoint_uuid=endpoint_id
    )
    get_task_log_task_id = globus_compute_wrapped_run(
        globus_compute_client,
        endpoint_id=endpoint_id,
        function_id=get_task_log_func_id,
        user_endpoint_config=user_endpoint_config,
        kwargs={"log_file_path": log_path},
    )

    fallback_result = {
        "content": "Failed to load log content within time limit",
        "is_complete": False,
    }
    for _ in range(max_attempts):
        try:
            log_result = globus_compute_client.get_result(get_task_log_task_id)
        except TaskPending:
            time.sleep(retry_sleep_seconds)
            continue
        except Exception:
            logger.exception("Failed to read log for path: %s", log_path)
            return fallback_result

        if isinstance(log_result, dict):
            return {
                "content": log_result.get("content", ""),
                "is_complete": bool(log_result.get("is_complete", False)),
            }
        return {"content": str(log_result), "is_complete": False}

    return fallback_result
