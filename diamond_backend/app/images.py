import logging
import os
import time

from flask import jsonify, request

from diamond_backend.app import app, g_database
from diamond_backend.app.utils.config_loader import (
    load_container_module_command,
)
from diamond_backend.app.utils.decorators import authenticated
from diamond_backend.app.utils.functions import (
    _make_shell_function,
    log_reader_wrapper,
)
from diamond_backend.app.utils.login_flow import initialize_globus_compute_client
from diamond_backend.app.utils.scripts_render import (
    render_apptainer_build_script,
    render_build_container_script,
)

logger = logging.getLogger(__name__)


@app.route("/api/image_builder", methods=["POST"])
@authenticated
def diamond_endpoint_image_builder():
    endpoint_id = request.json.get("endpoint")
    name = request.json.get("name")
    base_image = request.json.get("base_image")
    dependencies = request.json.get("dependencies")
    environment = request.json.get("environment")
    commands = request.json.get("commands")
    account = request.json.get("account")
    reservation = request.json.get("reservation")
    partition = request.json.get("partition")
    identity_id = request.cookies.get("primary_identity")
    time_duration = request.json.get("time_duration", "00:30:00")

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
        identity_id: {identity_id}
        time_duration: {time_duration}"""
    )
    # First we create the def file using ShellFunction.
    globus_compute_client = initialize_globus_compute_client()
    location = g_database.get_diamond_dir(
        endpoint_uuid=endpoint_id, identity_id=identity_id
    )
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
    def_file_creation_task_id = globus_compute_client.run(
        endpoint_id=endpoint_id,
        function_id=def_file_creation_function_id,
    )
    # Wait for the def file creation task to complete.
    def_file_creation_task_status = globus_compute_client.get_task(
        def_file_creation_task_id
    )
    while def_file_creation_task_status["pending"]:
        time.sleep(2)
        def_file_creation_task_status = globus_compute_client.get_task(
            def_file_creation_task_id
        )
        continue

    if reservation and reservation != "":
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
    )
    container_builder_shell = _make_shell_function(build_container_script)

    function_id = globus_compute_client.register_function(container_builder_shell)
    container_task_id = globus_compute_client.run(
        endpoint_id=endpoint_id, function_id=function_id
    )

    g_database.save_container(
        container_task_id=container_task_id,
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
    return jsonify({"task_id": container_task_id, "container_name": name})


@app.route("/api/get_build_log", methods=["GET"])
@authenticated
def get_build_log():
    """Get the content of a container build log file."""
    globus_compute_client = initialize_globus_compute_client()

    # Get parameters from request
    container_name = request.args.get("container_name")
    endpoint_id = request.args.get("endpoint_id")
    build_task_id = request.args.get("task_id")  # Original build task ID
    log_task_id = request.args.get("log_task_id")  # Previous log reader
    log_type = request.args.get("log_type")
    identity_id = request.cookies.get("primary_identity")
    logger.info(f"Log type: {log_type}")

    location = g_database.get_diamond_dir(
        endpoint_uuid=endpoint_id, identity_id=identity_id
    )
    log_file_path = ""
    if log_type == "stdout":
        log_file_path = location + "/logs" + "/" + container_name + ".stdout"
    elif log_type == "stderr":
        log_file_path = location + "/logs" + "/" + container_name + ".stderr"

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
            log_task_id = globus_compute_client.run(
                endpoint_id=endpoint_id,
                function_id=get_build_log.log_reader_function_id,
                log_file_path=log_file_path,
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
                new_log_task_id = globus_compute_client.run(
                    endpoint_id=endpoint_id,
                    function_id=get_build_log.log_reader_function_id,
                    log_file_path=log_file_path,
                )
            except Exception as e:
                logger.error(f"Error getting log result: {e}")
                log_result = {"content": "", "is_complete": False}
                new_log_task_id = log_task_id
        else:
            new_log_task_id = log_task_id

        # Check build task status if available
        build_status = "running"
        if build_task_id:
            try:
                build_task_status = globus_compute_client.get_task(build_task_id)
                build_status = build_task_status.get("status", "running")
            except Exception as e:
                logger.error(f"Error getting build status: {e}")
                return jsonify({"status": "error", "error": str(e)}), 500

        # Determine overall status
        if log_result and log_result.get("is_complete"):
            status = "completed"
        elif build_status in ["failed", "error"]:
            status = build_status
        else:
            status = "running"

        return jsonify(
            {
                "status": status,
                "log_content": log_result.get("content", "") if log_result else "",
                "build_task_id": build_task_id,
                "log_task_id": new_log_task_id,
            }
        )

    except Exception as e:
        logger.error(f"Error getting build log: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500
