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
from diamond_backend.app.utils.decorators import authenticated
from diamond_backend.app.utils.functions import (
    _make_shell_function,
    get_task_log,
    get_task_status,
)
from diamond_backend.app.utils.login_flow import initialize_globus_compute_client
from diamond_backend.app.utils.scripts_render import (
    render_submit_task_script,
)

logger = logging.getLogger(__name__)
GET_TASK_STATUS_DTASK_TYPE = "get_task_status"
GET_TASK_STATUS_REDIS_TTL_SECONDS = 30


@app.route("/api/submit_task", methods=["POST"])
@authenticated
def diamond_endpoint_submit_job():
    endpoint_id = request.json.get("endpoint")
    task_name = request.json.get("taskName")
    partition = request.json.get("partition")
    account = request.json.get("account")
    reservation = request.json.get("reservation", "")
    container = request.json.get("container")
    task_command = request.json.get("task", "")
    num_of_nodes = request.json.get("num_of_nodes", "1")  # 1 node is a safe default
    time_duration = request.json.get("time_duration")
    slurm_options = request.json.get("slurm_options", "")
    identity_id = request.cookies.get("primary_identity")
    dataset_id = request.json.get("dataset_id")

    if reservation and reservation != "":
        reservation = "--reservation=" + reservation

    if dataset_id:
        dataset_system_path = g_database.get_dataset_by_id(dataset_id).system_path
    else:
        dataset_system_path = ""

    container_dir_path = g_database.get_container_path_by_name(container)
    container_path = os.path.join(container_dir_path, container + ".sif")
    logger.info(f"Submit task container path: {container_path}")

    globus_compute_client = initialize_globus_compute_client()
    location = g_database.get_diamond_dir(
        endpoint_uuid=endpoint_id, identity_id=identity_id
    )

    stdout_path = os.path.join(location, "logs", task_name + ".stdout")
    stderr_path = os.path.join(location, "logs", task_name + ".stderr")

    endpoint_host = g_database.get_endpoint_host(endpoint_uuid=endpoint_id)
    container_module_command = load_container_module_command(endpoint_host)
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
    submit_task_shell = _make_shell_function(submit_task_script)
    function_id = globus_compute_client.register_function(submit_task_shell)
    try:
        task_id = globus_compute_client.run(
            endpoint_id=endpoint_id,
            function_id=function_id,
        )
    except Exception as e:
        logger.exception("Failed to submit task to Globus Compute")
        return jsonify(
            {"status": e.http_status, "messages": e.messages, "error": str(e)}
        ), e.http_status

    # Wait for submit task to complete with timeout to prevent hanging indefinitely
    max_attempts = 5
    submit_result = None
    for _ in range(max_attempts):
        try:
            submit_result = globus_compute_client.get_result(task_id)
            logger.info(f"Submit result: {globus_compute_client.get_task(task_id)}")
        except TaskPending:
            time.sleep(3)
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

    logger.debug(f"SUBMIT RESULT: {submit_result}")

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
    logger.info(f"SLURM job ID: {slurm_job_id}")

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
        checkpoint_path="",  # Will be set by backend
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
        task_status_func_id = globus_compute_client.register_function(get_task_status)
        task_records = []

        for task in tasks:
            try:
                task_status_task_id = globus_compute_client.run(
                    endpoint_id=task.compute_endpoint_id,
                    function_id=task_status_func_id,
                    task_name=task.task_name,
                )
            except Exception as e:
                logger.warning(
                    "Failed to submit get_task_status for task %s. Error: %s",
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

            task_status = getattr(task_status_result, "stdout", "").rstrip("\n")
            if task_status:
                if task_status == "COMPLETING":
                    task_status = "COMPLETED"
                g_database.update_task_status(task_record["task_id"], task_status)
                logger.info(task_status)
            else:
                previous_task_status = g_database.get_task_status(
                    task_record["task_id"]
                )
                if previous_task_status in ["RUNNING", "COMPLETING"]:
                    g_database.update_task_status(task_record["task_id"], "COMPLETED")
                    logger.info(f"Task {task_record['task_id']} completed")

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
        }
        for task in updated_tasks
    }

    logger.info(f"Updated task status response: {tasks_data}")
    return jsonify(tasks_data)


@app.route("/api/get_task_log", methods=["GET"])
@authenticated
def diamond_get_task_log():
    endpoint_id = request.args.get("endpoint_id")
    log_path = request.args.get("log_path")

    globus_compute_client = initialize_globus_compute_client()
    get_task_log_func_id = globus_compute_client.register_function(get_task_log)
    get_task_log_task_id = globus_compute_client.run(
        endpoint_id=endpoint_id,
        function_id=get_task_log_func_id,
        log_file_path=log_path,
    )
    max_attempts = 5
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
