import logging
import os
import re
import time

from flask import jsonify, request
from globus_compute_sdk.errors import TaskPending

from diamond_backend.app import app, g_database
from diamond_backend.app.utils.config_loader import (
    load_container_module_command,
)
from diamond_backend.app.utils.data_prep import globus_compute_wrapped_run
from diamond_backend.app.utils.decorators import authenticated
from diamond_backend.app.utils.functions import (
    _make_shell_function,
    fetch_task_status,
    log_reader_wrapper,
)
from diamond_backend.app.utils.login_flow import initialize_globus_compute_client
from diamond_backend.app.utils.scripts_render import (
    render_apptainer_build_script,
    render_build_container_script,
)

logger = logging.getLogger(__name__)

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
CONTAINER_TERMINAL_STATES = {"COMPLETED", "FAILED", "MISSING"}


def _is_trackable_batch_job_id(batch_job_id):
    normalized = str(batch_job_id or "").strip()
    return bool(normalized and normalized.isdigit())


def _parse_slurm_batch_job_id(submit_stdout):
    if not isinstance(submit_stdout, str):
        return None
    match = re.search(r"Submitted batch job (\d+)", submit_stdout)
    if not match:
        return None
    return match.group(1)


def _wait_for_globus_task_result(globus_compute_client, task_id, *, max_attempts=12):
    result = None
    for attempt in range(max_attempts):
        try:
            result = globus_compute_client.get_result(task_id)
            break
        except TaskPending:
            time.sleep(min(attempt + 1, 5))
            continue
    return result


def _get_build_status_for_response(container_status):
    normalized_status = str(container_status or "").strip().upper()
    if normalized_status in {"FAILED", "MISSING"}:
        return "failed"
    if normalized_status == "COMPLETED":
        return "completed"
    if normalized_status == "PENDING":
        return "pending"
    if normalized_status in {"RUNNING", "COMPLETING"}:
        return "running"
    return "running"


def _refresh_container_status_from_slurm(
    *,
    globus_compute_client,
    identity_id,
    endpoint_id,
    container_name,
    batch_job_id,
):
    normalized_batch_job_id = str(batch_job_id or "").strip()
    if not _is_trackable_batch_job_id(normalized_batch_job_id):
        return None

    user_endpoint_config = g_database.get_endpoint_user_config(
        identity_id=identity_id, endpoint_uuid=endpoint_id
    )
    if not hasattr(_refresh_container_status_from_slurm, "fetch_status_func_id"):
        _refresh_container_status_from_slurm.fetch_status_func_id = (
            globus_compute_client.register_function(fetch_task_status)
        )
    fetch_status_func_id = _refresh_container_status_from_slurm.fetch_status_func_id
    try:
        status_task_id = globus_compute_wrapped_run(
            globus_compute_client,
            endpoint_id=endpoint_id,
            function_id=fetch_status_func_id,
            user_endpoint_config=user_endpoint_config,
            kwargs={"batch_job_id": normalized_batch_job_id},
        )
    except Exception as e:
        logger.warning(
            "Failed to submit fetch_task_status for container %s. Error: %s",
            container_name,
            e,
        )
        return None

    status_result = _wait_for_globus_task_result(
        globus_compute_client, status_task_id, max_attempts=5
    )
    if status_result is None:
        return None

    slurm_state = getattr(status_result, "stdout", "").strip()
    if slurm_state:
        mapped_status = SLURM_STATE_MAPPING.get(slurm_state, "MISSING")
    else:
        container = g_database.get_container_by_name(container_name)
        previous_status = (getattr(container, "container_status", "") or "").upper()
        mapped_status = (
            "COMPLETED" if previous_status in {"RUNNING", "COMPLETING"} else None
        )

    if mapped_status:
        try:
            g_database.update_container_status_by_name(container_name, mapped_status)
        except Exception:
            logger.exception("Failed to update container status for %s", container_name)
    return mapped_status


@app.route("/api/image_builder", methods=["POST"])
@authenticated
def diamond_endpoint_image_builder():
    request_data = request.get_json(silent=True) or {}
    endpoint_id = request_data.get("endpoint")
    name = request_data.get("name")
    base_image = request_data.get("base_image")
    dependencies = request_data.get("dependencies")
    environment = request_data.get("environment")
    commands = request_data.get("commands")
    account = request_data.get("account")
    reservation = request_data.get("reservation")
    partition = request_data.get("partition")
    slurm_options = request_data.get("slurm_options", "")
    identity_id = request.cookies.get("primary_identity")
    time_duration = request_data.get("time_duration", "00:30:00")

    missing_fields = []
    if not endpoint_id:
        missing_fields.append("endpoint")
    if not name:
        missing_fields.append("name")
    if not base_image:
        missing_fields.append("base_image")
    if not partition:
        missing_fields.append("partition")
    if not account:
        missing_fields.append("account")
    if missing_fields:
        return (
            jsonify(
                {"error": "Missing required fields", "missing_fields": missing_fields}
            ),
            400,
        )

    logger.info(
        f""" Creating container with the following parameters:
        endpoint_id: {endpoint_id}
        container_name: {name}
        base_image: {base_image}
        dependencies: {dependencies}
        environment: {environment}
        commands: {commands}
        account: {account}
        reservation: {reservation}
        partition: {partition}
        slurm_options: {slurm_options}
        identity_id: {identity_id}
        time_duration: {time_duration}"""
    )

    globus_compute_client = initialize_globus_compute_client()
    location = g_database.get_diamond_dir(
        endpoint_uuid=endpoint_id, identity_id=identity_id
    )
    if not location:
        return jsonify({"error": "Diamond work directory is not configured"}), 400

    stdout_path = os.path.join(location, "logs", name + ".stdout")
    stderr_path = os.path.join(location, "logs", name + ".stderr")

    create_apptainer_def_script = render_apptainer_build_script(
        container_name=name,
        location=location,
        base_image=base_image,
        commands=commands,
        environment=environment,
    )
    create_apptainer_def_shell = _make_shell_function(create_apptainer_def_script)
    def_file_creation_function_id = globus_compute_client.register_function(
        create_apptainer_def_shell
    )
    user_endpoint_config = g_database.get_endpoint_user_config(
        identity_id=identity_id, endpoint_uuid=endpoint_id
    )
    def_file_creation_task_id = globus_compute_wrapped_run(
        globus_compute_client,
        endpoint_id=endpoint_id,
        function_id=def_file_creation_function_id,
        user_endpoint_config=user_endpoint_config,
    )
    def_creation_result = _wait_for_globus_task_result(
        globus_compute_client, def_file_creation_task_id
    )
    if def_creation_result is None:
        return jsonify(
            {"error": "Timed out while creating Apptainer definition file"}
        ), 500

    def_creation_stdout = getattr(def_creation_result, "stdout", "")
    def_creation_stderr = getattr(def_creation_result, "stderr", "")
    def_creation_returncode = getattr(def_creation_result, "returncode", None)
    if def_creation_returncode not in (None, 0):
        return jsonify(
            {
                "error": "Failed to create Apptainer definition file",
                "stdout": def_creation_stdout,
                "stderr": def_creation_stderr,
                "returncode": def_creation_returncode,
            }
        ), 500

    if reservation and reservation != "":
        reservation = str(reservation)
        if not reservation.startswith("--reservation="):
            reservation = "--reservation=" + reservation

    endpoint_host = g_database.get_endpoint_host(endpoint_uuid=endpoint_id)
    container_module_command = load_container_module_command(endpoint_host)
    build_container_script = render_build_container_script(
        container_name=name,
        location=location,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        time_duration=time_duration,
        partition=partition,
        account=account,
        reservation=reservation,
        container_module_command=container_module_command,
        slurm_options=slurm_options,
    )
    container_builder_shell = _make_shell_function(build_container_script)

    function_id = globus_compute_client.register_function(container_builder_shell)

    submit_build_task_id = globus_compute_wrapped_run(
        globus_compute_client,
        endpoint_id=endpoint_id,
        function_id=function_id,
        user_endpoint_config=user_endpoint_config,
    )
    submit_build_result = _wait_for_globus_task_result(
        globus_compute_client, submit_build_task_id
    )
    if submit_build_result is None:
        return jsonify({"error": "Timed out while submitting build job to SLURM"}), 500

    submit_stdout = getattr(submit_build_result, "stdout", "")
    submit_stderr = getattr(submit_build_result, "stderr", "")
    submit_returncode = getattr(submit_build_result, "returncode", None)
    if submit_returncode not in (None, 0):
        error_message = "Failed to submit build job to SLURM"
        if submit_stderr:
            error_message = f"{error_message}: {submit_stderr}"
        return jsonify(
            {
                "error": error_message,
                "stdout": submit_stdout,
                "stderr": submit_stderr,
                "returncode": submit_returncode,
            }
        ), 500

    slurm_job_id = _parse_slurm_batch_job_id(submit_stdout)
    if not slurm_job_id:
        return jsonify(
            {
                "error": "Failed to parse SLURM job ID from sbatch output",
                "stdout": submit_stdout,
                "stderr": submit_stderr,
                "returncode": submit_returncode,
            }
        ), 500

    g_database.save_container(
        container_task_id=slurm_job_id,
        container_status="PENDING",
        identity_id=identity_id,
        name=name,
        base_image=base_image,
        location=location,
        dependencies=dependencies,
        environment=environment,
        commands=commands,
        endpoint_id=endpoint_id,
        host=endpoint_host,
    )
    return jsonify(
        {
            "task_id": slurm_job_id,
            "container_name": name,
            "submit_task_id": submit_build_task_id,
        }
    )


@app.route("/api/get_build_log", methods=["GET"])
@authenticated
def get_build_log():
    """Get the content of a container build log file."""
    globus_compute_client = initialize_globus_compute_client()

    # Get parameters from request
    container_name = request.args.get("container_name")
    endpoint_id = request.args.get("endpoint_id")
    build_task_id = request.args.get("task_id")  # SLURM batch job ID
    log_task_id = request.args.get("log_task_id")  # Previous log reader
    log_type = request.args.get("log_type")
    identity_id = request.cookies.get("primary_identity")
    logger.info(f"Log type: {log_type}")

    if not container_name or not endpoint_id:
        return jsonify({"error": "container_name and endpoint_id are required"}), 400

    location = g_database.get_diamond_dir(
        endpoint_uuid=endpoint_id, identity_id=identity_id
    )
    if not location:
        return jsonify({"error": "Diamond work directory is not configured"}), 400
    log_file_path = ""
    if log_type == "stdout":
        log_file_path = location + "/logs" + "/" + container_name + ".stdout"
    elif log_type == "stderr":
        log_file_path = location + "/logs" + "/" + container_name + ".stderr"

    user_endpoint_config = g_database.get_endpoint_user_config(
        identity_id=identity_id, endpoint_uuid=endpoint_id
    )

    if not log_file_path:
        return jsonify({"error": "Missing required parameters"}), 400

    try:
        # Register function only once and store its ID
        if not hasattr(get_build_log, "log_reader_function_id"):
            get_build_log.log_reader_function_id = (
                globus_compute_client.register_function(log_reader_wrapper)
            )
            logger.info(
                f"Registered log reader function: {get_build_log.log_reader_function_id}"
            )

        # Create new log reader task if no log_task_id
        if not log_task_id:
            log_task_id = globus_compute_wrapped_run(
                globus_compute_client,
                endpoint_id=endpoint_id,
                function_id=get_build_log.log_reader_function_id,
                user_endpoint_config=user_endpoint_config,
                kwargs={"log_file_path": log_file_path},
            )
            logger.info(f"Created new log reader task: {log_task_id}")

        # Get status of current log reader task
        log_task_status = globus_compute_client.get_task(log_task_id)
        logger.info(f"Log task status: {log_task_status}")

        # Get log content if task completed
        log_result = None
        if log_task_status.get("status") == "success":
            try:
                log_result = globus_compute_client.get_result(log_task_id)
                logger.info(f"Log result: {log_result}")

                # Create new task using the same function ID
                new_log_task_id = globus_compute_wrapped_run(
                    globus_compute_client,
                    endpoint_id=endpoint_id,
                    function_id=get_build_log.log_reader_function_id,
                    user_endpoint_config=user_endpoint_config,
                    kwargs={"log_file_path": log_file_path},
                )
            except Exception as e:
                logger.error(f"Error getting log result: {e}")
                log_result = {"content": "", "is_complete": False}
                new_log_task_id = log_task_id
        else:
            new_log_task_id = log_task_id

        container = g_database.get_container_by_name(container_name)
        current_status = str(
            getattr(container, "container_status", "") or "PENDING"
        ).upper()
        resolved_task_id = str(
            build_task_id or getattr(container, "container_task_id", "") or ""
        ).strip()

        refreshed_status = None
        if current_status not in CONTAINER_TERMINAL_STATES and resolved_task_id:
            refreshed_status = _refresh_container_status_from_slurm(
                globus_compute_client=globus_compute_client,
                identity_id=identity_id,
                endpoint_id=endpoint_id,
                container_name=container_name,
                batch_job_id=resolved_task_id,
            )
        if refreshed_status:
            current_status = refreshed_status

        if log_result and log_result.get("is_complete"):
            current_status = "COMPLETED"
            try:
                g_database.update_container_status_by_name(container_name, "COMPLETED")
            except Exception:
                logger.exception(
                    "Failed to mark container %s as COMPLETED after log EOF",
                    container_name,
                )

        status = _get_build_status_for_response(current_status)

        return jsonify(
            {
                "status": status,
                "log_content": log_result.get("content", "") if log_result else "",
                "build_task_id": resolved_task_id,
                "log_task_id": new_log_task_id,
            }
        )

    except Exception as e:
        logger.error(f"Error getting build log: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500
