import logging
import os
import re
import time

from flask import jsonify, request
from globus_compute_sdk.errors import TaskPending

from diamond_backend.app import app, g_database, g_runtime_redis
from diamond_backend.app.errors import RequestMalformed
from diamond_backend.app.utils.config_loader import (
    load_container_module_command,
)
from diamond_backend.app.utils.decorators import authenticated
from diamond_backend.app.utils.functions import (
    _make_shell_function,
    get_container_status,
    log_reader_wrapper,
)
from diamond_backend.app.utils.login_flow import initialize_globus_compute_client
from diamond_backend.app.utils.scripts_render import (
    render_apptainer_build_script,
    render_build_container_script,
)

logger = logging.getLogger(__name__)
GET_CONTAINER_STATUS_DTASK_TYPE = "get_container_status"
GET_CONTAINER_STATUS_REDIS_TTL_SECONDS = 30
IMAGE_BUILDER_MAX_ATTEMPTS = 5
IMAGE_BUILDER_WAIT_SECONDS = 3


def _update_container_status_interactive(identity_id, globus_compute_client):
    redis_key = f"dtask:{identity_id}:{GET_CONTAINER_STATUS_DTASK_TYPE}"
    runtime_record = g_runtime_redis.get(redis_key)

    if runtime_record is None:
        containers = g_database.load_containers(identity_id=identity_id)
        task_status_func_id = globus_compute_client.register_function(
            get_container_status
        )
        task_records = []

        for container in containers:
            if not container.endpoint_id or not container.name:
                continue
            try:
                task_status_task_id = globus_compute_client.run(
                    endpoint_id=container.endpoint_id,
                    function_id=task_status_func_id,
                    name=container.name,
                )
            except Exception as e:
                logger.warning(
                    "Failed to submit get_container_status for container %s. Error: %s",
                    container.name,
                    e,
                )
                continue

            task_records.append(
                {
                    "identity_id": identity_id,
                    "dtask_type": GET_CONTAINER_STATUS_DTASK_TYPE,
                    "container_task_id": container.container_task_id,
                    "container_name": container.name,
                    "task_status_task_id": task_status_task_id,
                }
            )

        if task_records:
            g_runtime_redis.set(
                redis_key,
                task_records,
                ttl_seconds=GET_CONTAINER_STATUS_REDIS_TTL_SECONDS,
            )
        return

    pending_task_records = []
    for task_record in runtime_record:
        task_status_task_id = task_record["task_status_task_id"]
        try:
            task_status_task = globus_compute_client.get_task(task_status_task_id)
        except Exception as e:
            logger.warning(
                "Failed to load container status task %s. Error: %s",
                task_status_task_id,
                e,
            )
            continue

        if task_status_task.get("pending", False):
            pending_task_records.append(task_record)
            continue

        try:
            task_status_result = globus_compute_client.get_result(task_status_task_id)
        except Exception as e:
            logger.warning(
                "Failed to fetch result for container status task %s. Error: %s",
                task_status_task_id,
                e,
            )
            continue

        container_status = getattr(task_status_result, "stdout", "").rstrip("\n")
        if container_status:
            if container_status == "COMPLETING":
                container_status = "COMPLETED"
            g_database.update_container_status(
                task_record["container_task_id"], container_status
            )
            logger.info(container_status)
        else:
            container = g_database.get_container_by_name(task_record["container_name"])
            if container and container.container_status in ["RUNNING", "COMPLETING"]:
                g_database.update_container_status(
                    task_record["container_task_id"], "COMPLETED"
                )
                logger.info("Container %s completed", task_record["container_task_id"])

    if pending_task_records:
        g_runtime_redis.set(
            redis_key,
            pending_task_records,
            ttl_seconds=GET_CONTAINER_STATUS_REDIS_TTL_SECONDS,
        )
    else:
        g_runtime_redis.delete(redis_key)


def _serialize_containers(containers, current_identity=None, existing=None):
    containers_data = existing if existing is not None else {}
    endpoint_host_cache = {}

    for container in containers:
        host_name = getattr(container, "host", None) or ""
        endpoint_uuid = getattr(container, "endpoint_id", None)
        if not host_name and endpoint_uuid:
            if endpoint_uuid not in endpoint_host_cache:
                endpoint_host_cache[endpoint_uuid] = (
                    g_database.get_endpoint_host(endpoint_uuid=endpoint_uuid) or ""
                )
            host_name = endpoint_host_cache[endpoint_uuid]

        containers_data[container.name] = {
            "container_task_id": container.container_task_id,
            "status": container.container_status or "",
            "base_image": container.base_image,
            "location": container.location,
            "host_name": host_name,
            "is_public": bool(getattr(container, "is_public", False)),
            "owner_identity_id": getattr(container, "identity_id", None),
            "is_owner": (
                current_identity is not None
                and container.identity_id == current_identity
            ),
        }
    return containers_data


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
    def_file_creation_result = None
    for _ in range(IMAGE_BUILDER_MAX_ATTEMPTS):
        try:
            def_file_creation_result = globus_compute_client.get_result(
                def_file_creation_task_id
            )
        except TaskPending:
            time.sleep(IMAGE_BUILDER_WAIT_SECONDS)
            continue
        except Exception as e:
            logger.exception(
                "Failed to fetch def file creation result for task_id: %s",
                def_file_creation_task_id,
            )
            return (
                jsonify(
                    {
                        "error": "Failed to create apptainer definition file",
                        "task_id": def_file_creation_task_id,
                        "details": str(e),
                    }
                ),
                500,
            )
        else:
            break

    if def_file_creation_result is None:
        return (
            jsonify(
                {
                    "error": "Failed to create apptainer definition file - task timed out after maximum attempts",
                    "task_id": def_file_creation_task_id,
                }
            ),
            500,
        )

    def_stdout = getattr(def_file_creation_result, "stdout", "")
    def_stderr = getattr(def_file_creation_result, "stderr", "")
    def_returncode = getattr(def_file_creation_result, "returncode", None)
    if def_returncode not in (None, 0):
        return (
            jsonify(
                {
                    "error": "Failed to create apptainer definition file",
                    "stdout": def_stdout,
                    "stderr": def_stderr,
                    "returncode": def_returncode,
                }
            ),
            500,
        )

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

    submit_result = None
    for _ in range(IMAGE_BUILDER_MAX_ATTEMPTS):
        try:
            submit_result = globus_compute_client.get_result(container_task_id)
        except TaskPending:
            time.sleep(IMAGE_BUILDER_WAIT_SECONDS)
            continue
        except Exception as e:
            logger.exception(
                "Failed to fetch container submission result for task_id: %s",
                container_task_id,
            )
            return (
                jsonify(
                    {
                        "error": "Failed to submit image build job",
                        "task_id": container_task_id,
                        "details": str(e),
                    }
                ),
                500,
            )
        else:
            break

    if submit_result is None:
        return (
            jsonify(
                {
                    "error": "Failed to submit image build job - task timed out after maximum attempts",
                    "task_id": container_task_id,
                }
            ),
            500,
        )

    submit_stdout = getattr(submit_result, "stdout", "")
    submit_stderr = getattr(submit_result, "stderr", "")
    submit_returncode = getattr(submit_result, "returncode", None)
    if submit_returncode not in (None, 0):
        return (
            jsonify(
                {
                    "error": "Failed to submit image build job",
                    "stdout": submit_stdout,
                    "stderr": submit_stderr,
                    "returncode": submit_returncode,
                }
            ),
            500,
        )

    # Capture SLURM job id when available for debugging and client visibility.
    batch_job_id = None
    match = re.search(r"Submitted batch job (\d+)", submit_stdout)
    if match:
        batch_job_id = match.group(1)

    g_database.save_container(
        container_task_id=container_task_id,
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
    response = {"task_id": container_task_id, "container_name": name}
    if batch_job_id is not None:
        response["batch_job_id"] = batch_job_id
    return jsonify(response)


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


@app.route("/api/get_all_containers", methods=["GET"])
@authenticated
def get_all_containers():
    identity_id = request.cookies.get("primary_identity")
    logger.info(f"Loading all containers for identity_id: {identity_id}")
    globus_compute_client = initialize_globus_compute_client()
    _update_container_status_interactive(identity_id, globus_compute_client)
    containers = g_database.load_containers(identity_id=identity_id)
    containers_data = _serialize_containers(containers, current_identity=identity_id)

    managed_hosts = set()
    for endpoint in g_database.get_endpoints(identity_id=identity_id):
        if getattr(endpoint, "is_managed", False) and endpoint.endpoint_host:
            managed_hosts.add(endpoint.endpoint_host)
    public_by_host = {}
    if managed_hosts:
        public_containers = g_database.load_public_containers_by_hosts(
            hosts=list(managed_hosts), exclude_identity_id=identity_id
        )
        serialized_public = _serialize_containers(
            public_containers, current_identity=identity_id
        )
        for name, data in serialized_public.items():
            host = data.get("host_name") or "Unknown Host"
            if host not in public_by_host:
                public_by_host[host] = {}
            public_by_host[host][name] = data

    logger.info(
        f"Loaded {len(containers_data)} private containers and public groups for identity_id: {identity_id}"
    )
    return jsonify(
        {
            "containers": containers_data,
            "public_by_host": public_by_host,
        }
    )


@app.route("/api/get_containers_on_endpoint", methods=["POST"])
@authenticated
def get_containers_on_endpoint():
    identity_id = request.cookies.get("primary_identity")
    request_data = request.get_json() or {}
    endpoint_uuid = request_data.get("endpoint_uuid")
    if not endpoint_uuid:
        raise RequestMalformed("endpoint_uuid")

    globus_compute_client = initialize_globus_compute_client()
    _update_container_status_interactive(identity_id, globus_compute_client)

    logger.info(
        f"Loading containers for identity_id: {identity_id} on endpoint: {endpoint_uuid}"
    )
    containers = g_database.load_containers_by_endpoint(
        identity_id=identity_id, endpoint_uuid=endpoint_uuid
    )
    containers_data = _serialize_containers(containers, current_identity=identity_id)

    endpoint_host = g_database.get_endpoint_host(endpoint_uuid=endpoint_uuid)
    public_containers_data = {}
    if endpoint_host:
        public_containers = g_database.load_public_containers_by_hosts(
            hosts=[endpoint_host], exclude_identity_id=identity_id
        )
        if public_containers:
            public_containers_data = _serialize_containers(
                public_containers,
                current_identity=identity_id,
            )

    logger.info(
        f"Loaded {len(containers_data)} private and {len(public_containers_data)} public containers for endpoint {endpoint_uuid}"
    )
    return jsonify(
        {
            "private": containers_data,
            "public": public_containers_data,
        }
    )


@app.route("/api/delete_container", methods=["POST"])
@authenticated
def diamond_delete_container():
    container_id = request.json.get("containerId")
    g_database.delete_container(container_id)
    logger.info(f"container {container_id} deleted")
    return jsonify({"message": "Container deleted successfully"})


@app.route("/api/publish_container", methods=["POST"])
@authenticated
def publish_container():
    return (
        jsonify(
            {
                "error": "Publishing containers is currently disabled. Please use an existing public image."
            }
        ),
        403,
    )
