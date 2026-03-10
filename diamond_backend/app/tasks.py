import logging
import os
import re
import time
from datetime import datetime

from flask import jsonify, request
from globus_compute_sdk.errors import TaskPending

from diamond_backend.app import app, g_database, g_runtime_redis
from diamond_backend.app.utils.config_loader import (
    load_container_module_command,
)
from diamond_backend.app.utils.data_prep import globus_compute_wrapped_run
from diamond_backend.app.utils.decorators import authenticated
from diamond_backend.app.utils.functions import (
    _escape_shell_braces,
    _make_shell_function,
    fetch_task_status,
    get_task_log,
)
from diamond_backend.app.utils.login_flow import initialize_globus_compute_client
from diamond_backend.app.utils.scripts_render import (
    render_submit_task_script,
    render_task_template_script,
)

logger = logging.getLogger(__name__)
GET_TASK_STATUS_DTASK_TYPE = "fetch_task_status"
GET_TASK_STATUS_REDIS_TTL_SECONDS = 30

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

TERMINAL_STATES = ["COMPLETED", "COMPLETING", "FAILED", "MISSING"]
FINETUNED_MODEL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
ARTIFACT_PATH_MARKER_PATTERN = re.compile(r"^DIAMOND_ARTIFACT_PATH=(.+)$", re.MULTILINE)


def _validate_finetuned_model_name(value):
    if not isinstance(value, str):
        raise ValueError("finetuned_model_name must be a non-empty string")

    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError("finetuned_model_name must be a non-empty string")
    if normalized_value in {".", ".."}:
        raise ValueError("finetuned_model_name cannot be '.' or '..'")
    if "/" in normalized_value or "\\" in normalized_value:
        raise ValueError("finetuned_model_name cannot contain path separators")
    if not FINETUNED_MODEL_NAME_PATTERN.fullmatch(normalized_value):
        raise ValueError(
            "finetuned_model_name can only contain letters, numbers, '.', '-', '_'"
        )

    return normalized_value


def _build_finetuned_artifact_path(*, finetuned_model_path, finetuned_model_name):
    if not finetuned_model_path or not finetuned_model_name:
        return ""
    return os.path.join(str(finetuned_model_path).strip(), finetuned_model_name)


def _extract_artifact_path_from_submit_stdout(submit_stdout):
    if not isinstance(submit_stdout, str):
        return ""
    match = ARTIFACT_PATH_MARKER_PATTERN.search(submit_stdout)
    if not match:
        return ""
    return match.group(1).strip()


@app.route("/api/submit_task", methods=["POST"])
@authenticated
def diamond_endpoint_submit_job():
    request_data = request.get_json(silent=True) or {}
    task_define = request_data.get("task_define") or {}
    if not isinstance(task_define, dict):
        return jsonify({"error": "task_define must be a JSON object"}), 400

    def pick_field(*keys, default=None):
        for key in keys:
            value = request_data.get(key)
            if value not in (None, ""):
                return value
        for key in keys:
            value = task_define.get(key)
            if value not in (None, ""):
                return value
        return default

    def pick_raw_field(*keys):
        for key in keys:
            if key in request_data:
                return True, request_data.get(key)
        for key in keys:
            if key in task_define:
                return True, task_define.get(key)
        return False, None

    endpoint_id = pick_field("endpoint")
    task_name = pick_field("taskName", "task_name")
    partition = pick_field("partition")
    account = pick_field("account")
    reservation = pick_field("reservation", default="")
    container_name = pick_field("container", "container_name")
    task_command = pick_field("task", "task_command", default="")
    num_of_nodes = pick_field("num_of_nodes", default="1")  # 1 node is a safe default
    time_duration = pick_field("time_duration")
    slurm_options = pick_field("slurm_options", default="")
    task_template_name = pick_field("task_template")
    identity_id = request.cookies.get("primary_identity")
    dataset_id = pick_field("dataset_id")
    finetuned_model_path = pick_field("finetuned_model_path", default="")
    finetuned_model_name_present, raw_finetuned_model_name = pick_raw_field(
        "finetuned_model_name"
    )
    finetuned_model_name = None
    if finetuned_model_name_present:
        try:
            finetuned_model_name = _validate_finetuned_model_name(
                raw_finetuned_model_name
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
    artifact_path = _build_finetuned_artifact_path(
        finetuned_model_path=finetuned_model_path,
        finetuned_model_name=finetuned_model_name,
    )

    if not endpoint_id:
        return jsonify({"error": "endpoint is required"}), 400
    if not task_name:
        return jsonify({"error": "taskName is required"}), 400

    if reservation and reservation != "":
        reservation = str(reservation)
        if not reservation.startswith("--reservation="):
            reservation = "--reservation=" + reservation

    dataset_path = pick_field("dataset_path", "dataset_system_path", default="")

    if dataset_id:
        dataset_system_path = g_database.get_dataset_by_id(dataset_id).system_path
    else:
        dataset_system_path = dataset_path

    if not dataset_path:
        dataset_path = dataset_system_path

    container_path = ""
    if task_template_name:
        container_path = pick_field("container_path", default="")
        if not container_path and container_name:
            try:
                container_dir_path = g_database.get_container_path_by_name(
                    container_name
                )
                container_path = os.path.join(
                    container_dir_path, container_name + ".sif"
                )
                logger.info(f"Submit task container path: {container_path}")
            except Exception:
                container_path = str(container_name)
    elif container_name:
        container_dir_path = g_database.get_container_path_by_name(container_name)
        container_path = os.path.join(container_dir_path, container_name + ".sif")
        logger.info(f"Submit task container path: {container_path}")

    if not task_template_name:
        missing_fields = []
        if not partition:
            missing_fields.append("partition")
        if not account:
            missing_fields.append("account")
        if not container_name:
            missing_fields.append("container")
        if not time_duration:
            missing_fields.append("time_duration")
        if missing_fields:
            return (
                jsonify(
                    {
                        "error": "Missing required fields for default submit_task template",
                        "missing_fields": missing_fields,
                    }
                ),
                400,
            )

    task_name = str(task_name)

    globus_compute_client = initialize_globus_compute_client()
    location = g_database.get_diamond_dir(
        endpoint_uuid=endpoint_id, identity_id=identity_id
    )
    user_endpoint_config = g_database.get_endpoint_user_config(
        identity_id=identity_id, endpoint_uuid=endpoint_id
    )

    stdout_path = os.path.join(location, "logs", task_name + ".stdout")
    stderr_path = os.path.join(location, "logs", task_name + ".stderr")

    endpoint_host = g_database.get_endpoint_host(endpoint_uuid=endpoint_id)
    container_module_command = load_container_module_command(endpoint_host)
    if task_template_name:
        render_context = {
            **task_define,
            "task_name": task_name,
            "taskName": task_name,
            "location": location,
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
            "time_duration": time_duration,
            "partition": partition,
            "account": account,
            "reservation": reservation,
            "num_of_nodes": num_of_nodes,
            "container": container_path,
            "container_name": container_name,
            "container_path": container_path,
            "container_module_command": container_module_command,
            "dataset_system_path": dataset_system_path,
            "dataset_path": dataset_path,
            "task_command": task_command,
            "slurm_options": slurm_options,
        }
        if finetuned_model_name is not None:
            render_context["finetuned_model_name"] = finetuned_model_name
        if finetuned_model_path:
            render_context["finetuned_model_path"] = str(finetuned_model_path).strip()
        try:
            submit_task_script = render_task_template_script(
                str(task_template_name), render_context
            )
        except Exception as e:
            logger.exception("Failed to render task template: %s", task_template_name)
            return jsonify({"error": f"Failed to render task template: {e}"}), 400
    else:
        submit_task_script = render_submit_task_script(
            task_name=task_name,
            location=location,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            time_duration=time_duration,
            partition=partition,
            account=account,
            reservation=reservation,
            num_of_nodes=num_of_nodes,
            container_module_command=container_module_command,
            container=container_path,
            dataset_system_path=dataset_system_path,
            task_command=task_command,
            slurm_options=slurm_options,
        )
    logger.info(f"Submit task script: {submit_task_script}")
    submit_task_shell = _make_shell_function(_escape_shell_braces(submit_task_script))
    function_id = globus_compute_client.register_function(submit_task_shell)
    try:
        task_id = globus_compute_wrapped_run(
            globus_compute_client,
            endpoint_id=endpoint_id,
            function_id=function_id,
            user_endpoint_config=user_endpoint_config,
        )
    except Exception as e:
        logger.exception("Failed to submit task to Globus Compute")
        return jsonify(
            {"status": e.http_status, "messages": e.messages, "error": str(e)}
        ), e.http_status

    # Wait for submit task to complete with timeout to prevent hanging indefinitely
    max_attempts = 12
    submit_result = None
    # Wait for a max of ~60s, with linear backoff
    for i in range(max_attempts):
        try:
            submit_result = globus_compute_client.get_result(task_id)
            logger.debug("Submit result: {}".format(submit_result))
        except TaskPending:
            time.sleep(i)
            continue
        except Exception as e:
            logger.exception("Failed to fetch results for task_id: %s", task_id)
            return jsonify(
                {
                    "error": "Failed to submit job - could not fetch results from endpoint",
                    "task_id": task_id,
                    "details": str(e),
                }
            ), 500
        else:
            break

    if submit_result is None:
        return jsonify(
            {
                "error": "Failed to submit job - task timed out after maximum attempts",
                "task_id": task_id,
            }
        ), 500

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
        return jsonify(
            {
                "error": error_message,
                "stdout": submit_stdout,
                "stderr": submit_stderr,
                "returncode": submit_returncode,
            }
        ), 500

    rendered_artifact_path = _extract_artifact_path_from_submit_stdout(submit_stdout)
    if rendered_artifact_path:
        artifact_path = rendered_artifact_path

    # Parse SLURM job ID from output - currently only supporting SLURM-based systems
    match = re.search(r"Submitted batch job (\d+)", submit_stdout)
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
        return jsonify(
            {
                "error": error_message,
                "stdout": submit_stdout,
                "stderr": submit_stderr,
                "returncode": submit_returncode,
            }
        ), 500

    slurm_job_id = match.group(1)
    logger.info("Task:{} is mapped to SLURM job ID:{}".format(task_id, slurm_job_id))

    g_database.save_task(
        task_id=task_id,
        batch_job_id=slurm_job_id,
        task_name=task_name,
        identity_id=identity_id,
        task_status="PENDING",
        task_create_time=datetime.now(),
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        compute_endpoint_id=endpoint_id,
        checkpoint_path=artifact_path,
    )
    return jsonify(
        {
            "task_id": task_id,
            "batch_job_id": slurm_job_id,
            "task_name": task_name,
            "message": "Task submitted successfully",
        }
    )


@app.route("/api/get_task_status", methods=["GET"])
@authenticated
def diamond_get_task_status():
    identity_id = request.cookies.get("primary_identity")
    globus_compute_client = initialize_globus_compute_client()
    redis_key = f"dtask:{identity_id}:{GET_TASK_STATUS_DTASK_TYPE}"
    runtime_record = g_runtime_redis.get(redis_key)

    if runtime_record is None:
        tasks = g_database.load_tasks(identity_id=identity_id)
        task_status_func_id = globus_compute_client.register_function(fetch_task_status)
        task_records = []

        filtered_tasks = [
            task for task in tasks if task.task_status not in TERMINAL_STATES
        ]
        for task in filtered_tasks:
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
            except Exception as e:
                logger.warning(
                    "Failed to submit fetch_task_status for task %s. Error: %s",
                    task.task_id,
                    e,
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

        if task_records:
            g_runtime_redis.set(
                redis_key,
                task_records,
                ttl_seconds=GET_TASK_STATUS_REDIS_TTL_SECONDS,
            )
    else:
        pending_task_records = []
        for task_record in runtime_record:
            task_status_task_id = task_record["task_status_task_id"]
            task_status_task = None
            try:
                task_status_task = globus_compute_client.get_task(task_status_task_id)
            except Exception as e:
                logger.warning(
                    "Failed to load task status task %s. Error: %s",
                    task_status_task_id,
                    e,
                )
                continue

            if task_status_task.get("pending", False):
                pending_task_records.append(task_record)
                continue

            try:
                task_status_result = globus_compute_client.get_result(
                    task_status_task_id
                )
            except Exception as e:
                logger.warning(
                    "Failed to fetch result for task status task %s. Error: %s",
                    task_status_task_id,
                    e,
                )
                continue

            task_status = getattr(task_status_result, "stdout", "").strip()
            new_task_status = None
            if task_status:
                try:
                    new_task_status = SLURM_STATE_MAPPING[task_status]
                except KeyError as e:
                    new_task_status = "MISSING"
                    logger.exception(
                        "Failed to fetch task status for task status task %s. Error: %s",
                        task_status,
                        e,
                    )
                logger.debug(
                    f"Task:{task_record['task_id']} status {task_status} mapped to {new_task_status}"
                )
            else:
                try:
                    previous_task_status = g_database.get_task_status(
                        task_record["task_id"]
                    )
                except AttributeError:
                    logger.warning(f"Task:{task_record['task_id']} removed")
                    continue
                if previous_task_status in ["RUNNING", "COMPLETING"]:
                    new_task_status = "COMPLETED"
            if new_task_status:
                try:
                    g_database.update_task_status(
                        task_record["task_id"], new_task_status
                    )
                    logger.info(
                        f"Updating Task:{task_record['task_id']} to {new_task_status}"
                    )
                except Exception:
                    logger.exception(f"Failed to update task:{task_record['task_id']}")

        if pending_task_records:
            g_runtime_redis.set(
                redis_key,
                pending_task_records,
                ttl_seconds=GET_TASK_STATUS_REDIS_TTL_SECONDS,
            )
        else:
            g_runtime_redis.delete(redis_key)

    # Reload the updated tasks from the database
    updated_tasks = g_database.load_tasks(identity_id=identity_id)

    # Format tasks data for JSON response
    tasks_data = {
        task.task_id: {
            "task_id": task.task_id,
            "identity_id": task.identity_id,
            "task_name": task.task_name,
            "status": task.task_status,
            "details": {
                "endpoint_id": task.compute_endpoint_id or "N/A",
                "task_create_time": task.task_create_time,
            },
            "result": task.stdout_path,
            "error": task.stderr_path,
            "artifact_path": task.checkpoint_path,
        }
        for task in updated_tasks
    }

    logger.debug(f"Updated task status response: {tasks_data}")
    return jsonify(tasks_data)


@app.route("/api/get_task_log", methods=["GET"])
@authenticated
def diamond_get_task_log():
    identity_id = request.cookies.get("primary_identity")
    endpoint_id = request.args.get("endpoint_id")
    log_path = request.args.get("log_path")

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
    max_attempts = 5
    log_content = "Failed to load log content within time limit"
    for _ in range(max_attempts):
        try:
            log_content = globus_compute_client.get_result(get_task_log_task_id)[
                "content"
            ]
            logger.info(f"Log content: {log_content}")
            break
        except TaskPending:
            # TODO: remove sleep
            time.sleep(2)
            continue
    return jsonify({"log_content": log_content})


@app.route("/api/delete_task", methods=["POST"])
@authenticated
def diamond_delete_task():
    # TODO: Does this need to talk to Globus at all?
    task_id = request.json.get("taskId")
    g_database.delete_task(task_id)
    logger.info(f"task {task_id} deleted")
    return jsonify({"message": "Task deleted successfully"})
