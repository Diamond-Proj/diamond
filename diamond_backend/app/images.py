import logging
import os

from flask import jsonify, request

from diamond_backend.app import app, g_database
from diamond_backend.app.task_runtime import (
    TaskSubmissionError,
    read_remote_task_log,
    refresh_identity_task_statuses,
    submit_batch_script_task,
)
from diamond_backend.app.utils.config_loader import (
    load_container_module_command,
)
from diamond_backend.app.utils.decorators import authenticated
from diamond_backend.app.utils.scripts_render import (
    render_task_template_script,
)

logger = logging.getLogger(__name__)

CONTAINER_BUILD_TASK_TEMPLATE = "container-build.j2"
CONTAINER_BUILD_TERMINAL_STATES = {"COMPLETED", "FAILED", "MISSING"}


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
    identity_id = request.cookies.get("primary_identity")
    time_duration = request_data.get("time_duration", "00:30:00")

    missing_fields = [
        field_name
        for field_name, value in {
            "endpoint": endpoint_id,
            "name": name,
            "base_image": base_image,
            "partition": partition,
            "account": account,
        }.items()
        if value in (None, "")
    ]
    if missing_fields:
        return (
            jsonify(
                {
                    "error": "Missing required fields for image build",
                    "missing_fields": missing_fields,
                }
            ),
            400,
        )

    if reservation and not str(reservation).startswith("--reservation="):
        reservation = f"--reservation={reservation}"

    logger.info(
        """Creating container with the following parameters:
        endpoint_id: %s
        container_name: %s
        base_image: %s
        dependencies: %s
        environment: %s
        commands: %s
        account: %s
        reservation: %s
        partition: %s
        identity_id: %s
        time_duration: %s""",
        endpoint_id,
        name,
        base_image,
        dependencies,
        environment,
        commands,
        account,
        reservation,
        partition,
        identity_id,
        time_duration,
    )

    location = g_database.get_diamond_dir(
        endpoint_uuid=endpoint_id, identity_id=identity_id
    )
    stdout_path = os.path.join(location, "logs", name + ".stdout")
    stderr_path = os.path.join(location, "logs", name + ".stderr")
    artifact_path = os.path.join(location, name + ".sif")

    endpoint_host = g_database.get_endpoint_host(endpoint_uuid=endpoint_id)
    container_module_command = load_container_module_command(endpoint_host)
    submit_task_script = render_task_template_script(
        CONTAINER_BUILD_TASK_TEMPLATE,
        {
            "task_name": name,
            "container_name": name,
            "location": location,
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
            "time_duration": time_duration,
            "partition": partition,
            "account": account,
            "reservation": reservation or "",
            "container_module_command": container_module_command,
            "base_image": base_image,
            "commands": commands or "",
            "environment": environment or "",
        },
    )

    try:
        submission = submit_batch_script_task(
            endpoint_id=endpoint_id,
            identity_id=identity_id,
            task_name=name,
            submit_script=submit_task_script,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            checkpoint_path=artifact_path,
        )
    except TaskSubmissionError as exc:
        return jsonify(exc.to_response_payload()), exc.http_status

    g_database.save_container(
        container_task_id=submission["task_id"],
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
            "task_id": submission["task_id"],
            "batch_job_id": submission["batch_job_id"],
            "container_name": name,
            "message": "Container build submitted successfully",
        }
    )


@app.route("/api/get_build_log", methods=["GET"])
@authenticated
def get_build_log():
    identity_id = request.cookies.get("primary_identity")
    build_task_id = request.args.get("task_id")
    log_type = request.args.get("log_type")

    if not build_task_id:
        return jsonify({"error": "task_id is required"}), 400
    if log_type not in {"stdout", "stderr"}:
        return jsonify({"error": "log_type must be stdout or stderr"}), 400

    refresh_identity_task_statuses(identity_id)
    build_task = g_database.get_task(task_id=build_task_id, identity_id=identity_id)
    if not build_task:
        return jsonify({"error": f"Task {build_task_id} not found"}), 404

    endpoint_id = request.args.get("endpoint_id") or build_task.compute_endpoint_id
    log_path = (
        build_task.stdout_path if log_type == "stdout" else build_task.stderr_path
    )
    log_result = read_remote_task_log(
        identity_id=identity_id,
        endpoint_id=endpoint_id,
        log_path=log_path,
    )

    task_status = str(build_task.task_status or "").strip().upper()
    status = task_status.lower() if task_status else "unknown"
    if task_status in CONTAINER_BUILD_TERMINAL_STATES:
        status = "completed" if task_status == "COMPLETED" else "failed"

    return jsonify(
        {
            "status": status,
            "log_content": log_result.get("content", ""),
            "build_task_id": build_task_id,
        }
    )
