import json
import logging
import os
import re
import time
from datetime import datetime

import globus_sdk
from flask import jsonify, redirect, request
from globus_compute_sdk import ShellFunction
from globus_compute_sdk.errors import TaskPending

from diamond_backend.app import app, g_database
from diamond_backend.app.utils.config_loader import load_container_module_command
from diamond_backend.app.utils.data_prep import (
    load_accounts_partitions,
    register_all_endpoints,
)
from diamond_backend.app.utils.decorators import authenticated
from diamond_backend.app.utils.functions import (
    check_diamond_work_path,
    create_diamond_dir,
    get_task_status,
    log_reader_wrapper,
)
from diamond_backend.app.utils.host_machine_mapping import KNOWN_MACHINES
from diamond_backend.app.utils.login_flow import initialize_globus_compute_client
from diamond_backend.app.utils.scripts_render import (
    render_apptainer_build_script,
    render_build_container_script,
    render_submit_task_script,
)
from diamond_backend.app.utils.transfer import get_transfer_client
from diamond_backend.app.utils.utils import get_git_info

logger = logging.getLogger(__name__)

HOST = app.config.get("HOST")
AUTH_URL = app.config.get("AUTH_URL")
NEXT_URL = app.config.get("NEXT_URL")
RAILWAY_GIT_COMMIT_SHA = app.config.get("RAILWAY_GIT_COMMIT_SHA")

logger.info(f"HOST in routes.py: {HOST}")
logger.info(f"AUTH_URL in routes.py: {AUTH_URL}")
logger.info(f"NEXT_URL in routes.py: {NEXT_URL}")
logger.info(f"RAILWAY_GIT_COMMIT_SHA in routes.py: {RAILWAY_GIT_COMMIT_SHA}")


@app.route("/api/home", methods=["GET"])
def home():
    """Home route."""
    logger.info(f"Home route redirecting to {NEXT_URL}/sign-in")
    return redirect(NEXT_URL + "/sign-in")


@app.route("/api/healthcheck", methods=["GET"])
def healthcheck():
    """Health check endpoint."""
    logger.info("Health check route")

    # Get git information
    git_info = get_git_info()
    if git_info["commit_sha"] == "unknown":
        return jsonify(
            {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "git": git_info,
            }
        ), 500
    else:
        return jsonify(
            {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "git": git_info,
            }
        ), 200


@app.route("/api/is_authenticated", methods=["GET"])
@authenticated
def is_authenticated():
    return jsonify({"is_authenticated": True})


@app.route("/api/register_all_endpoints", methods=["POST"])
@authenticated
def diamond_register_all_endpoints():
    """Register all endpoints for a user"""
    identity_id = request.cookies.get("primary_identity")
    globus_compute_client = initialize_globus_compute_client()
    # Register endpoints and get all endpoints in one step
    all_endpoints = register_all_endpoints(
        globus_compute_client, identity_id, g_database, logger
    )
    return jsonify({"status": "success", "endpoints": all_endpoints}), 200


@app.route("/api/load_accounts_partitions", methods=["POST"])
@authenticated
def diamond_load_accounts_partitions():
    """Load accounts and partitions for an active endpoint"""
    identity_id = request.cookies.get("primary_identity")
    endpoint_uuid = request.json.get("endpoint_uuid")
    globus_compute_client = initialize_globus_compute_client()
    account_list, partition_list = load_accounts_partitions(
        endpoint_uuid, identity_id, g_database, logger, globus_compute_client
    )
    return jsonify(
        {
            "status": "success",
            "account_list": account_list,
            "partition_list": partition_list,
        }
    ), 200


@app.route("/api/list_all_endpoints", methods=["GET"])
@authenticated
def diamond_list_all_endpoints():
    identity_id = request.cookies.get("primary_identity")
    all_endpoints = []
    for endpoint in g_database.get_endpoints(identity_id=identity_id):
        all_endpoints.append(
            {
                "endpoint_name": endpoint.endpoint_name,
                "endpoint_uuid": endpoint.endpoint_uuid,
                "endpoint_host": endpoint.endpoint_host,
                "endpoint_status": endpoint.endpoint_status,
                "diamond_dir": endpoint.diamond_dir,
            }
        )

    sorted_endpoints = sorted(all_endpoints, key=lambda x: x["endpoint_name"])
    sorted_active_first_endpoints = sorted(
        sorted_endpoints, key=lambda x: x["endpoint_status"], reverse=True
    )
    return sorted_active_first_endpoints


@app.route("/api/list_active_endpoints", methods=["GET"])
@authenticated
def diamond_list_active_endpoints():
    identity_id = request.cookies.get("primary_identity")
    active_endpoints = []
    for endpoint in g_database.get_endpoints(identity_id=identity_id):
        if endpoint.endpoint_status == "online":
            active_endpoints.append(
                {
                    "endpoint_name": endpoint.endpoint_name,
                    "endpoint_uuid": endpoint.endpoint_uuid,
                    "endpoint_host": endpoint.endpoint_host,
                    "endpoint_status": endpoint.endpoint_status,
                    "diamond_dir": endpoint.diamond_dir,
                }
            )
        else:
            continue
    return active_endpoints


@app.route("/api/get_diamond_dir", methods=["GET"])
@authenticated
def diamond_get_diamond_dir():
    identity_id = request.cookies.get("primary_identity")
    endpoint_uuid = request.args.get("endpoint_uuid")
    diamond_dir = g_database.get_diamond_dir(
        identity_id=identity_id, endpoint_uuid=endpoint_uuid
    )
    return jsonify({"diamond_dir": diamond_dir})


@app.route("/api/set_diamond_work_path", methods=["POST"])
@authenticated
def diamond_set_diamond_work_path():
    identity_id = request.cookies.get("primary_identity")
    endpoint_uuid = request.json.get("endpoint_uuid")
    diamond_work_path = request.json.get("diamond_work_path")

    # Handle diamond path logic: if path ends with "diamond", don't add it again
    if diamond_work_path.endswith("diamond"):
        diamond_dir = diamond_work_path
        diamond_log_dir = os.path.join(diamond_work_path, "logs")
        diamond_image_dir = os.path.join(diamond_work_path, "images")
    else:
        diamond_dir = os.path.join(diamond_work_path, "diamond")
        diamond_log_dir = os.path.join(diamond_dir, "logs")
        diamond_image_dir = os.path.join(diamond_dir, "images")

    globus_compute_client = initialize_globus_compute_client()
    check_diamond_work_path_func_id = globus_compute_client.register_function(
        check_diamond_work_path
    )
    check_diamond_work_path_task_id = globus_compute_client.run(
        endpoint_id=endpoint_uuid,
        function_id=check_diamond_work_path_func_id,
        diamond_work_path=diamond_work_path,
    )
    check_diamond_work_path_task_status = globus_compute_client.get_task(
        check_diamond_work_path_task_id
    )
    while check_diamond_work_path_task_status["pending"]:
        time.sleep(2)
        check_diamond_work_path_task_status = globus_compute_client.get_task(
            check_diamond_work_path_task_id
        )
        continue
    check_diamond_work_path_task_result = globus_compute_client.get_result(
        check_diamond_work_path_task_id
    )
    if check_diamond_work_path_task_result == 0:
        return jsonify(
            {"error": "Diamond work path does not exist or is not writable"}
        ), 400
    create_diamond_dir_func_id = globus_compute_client.register_function(
        create_diamond_dir
    )
    globus_compute_client.run(
        endpoint_id=endpoint_uuid,
        function_id=create_diamond_dir_func_id,
        diamond_dir=diamond_dir,
        diamond_log_dir=diamond_log_dir,
        diamond_image_dir=diamond_image_dir,
    )

    g_database.save_diamond_dir(
        identity_id=identity_id,
        endpoint_uuid=endpoint_uuid,
        diamond_dir=diamond_dir,
    )
    return jsonify({"status": "success"})


def _validate_dataset_registration(
    data: dict, transfer_client
) -> tuple[str, int] | None:
    """Validate user dataset registration data."""
    if not data:
        return "No JSON data provided", 400

    required_fields = ["collection_uuid", "globus_path", "system_path", "machine_name"]
    for field in required_fields:
        if field not in data:
            return f"Missing required field: {field}", 400

    valid_machines = dict(KNOWN_MACHINES).values()
    if data["machine_name"] not in valid_machines:
        return f"Invalid machine_name. Must be one of: {', '.join(valid_machines)}", 400

    # dataset_metadata is valid JSON if provided
    dataset_metadata = data.get("dataset_metadata", "{}")
    if dataset_metadata:
        try:
            json.loads(dataset_metadata) if isinstance(
                dataset_metadata, str
            ) else dataset_metadata
        except json.JSONDecodeError:
            return "Metadata must be valid JSON", 400

    # ensure user can actually access the collection
    try:
        transfer_client.get_endpoint(data["collection_uuid"])
        logger.info(f"Collection {data['collection_uuid']} validation successful")
    except globus_sdk.GlobusAPIError as e:
        logger.error(f"Globus collection validation failed: {e}")
        if os.environ.get("FLASK_ENV") == "development":
            logger.warning(
                f"Ignoring failed access to collection {data['collection_uuid']} in development mode."
            )
            return None
        return f"Cannot access collection {data['collection_uuid']}: {str(e)}", 400

    return None


@app.route("/api/datasets", methods=["POST"])
@authenticated
def register_user_dataset():
    """Register a new user dataset."""
    try:
        data = request.get_json()

        identity_id = request.cookies.get("primary_identity")
        if not identity_id:
            return jsonify({"error": "No identity ID found"}), 400

        # Validate input data
        transfer_client = get_transfer_client(request)
        validation_error = _validate_dataset_registration(data, transfer_client)
        if validation_error is not None:
            error_msg, status_code = validation_error
            return jsonify({"error": error_msg}), status_code

        # Save dataset (public is always False for user datasets)
        g_database.save_dataset(
            collection_uuid=data["collection_uuid"],
            globus_path=data["globus_path"],
            system_path=data["system_path"],
            machine_name=data["machine_name"],
            dataset_metadata=data.get("dataset_metadata", "{}"),
            identity_id=identity_id,
            public=False,
            dataset_name=data.get("dataset_name"),
        )

        return jsonify(
            {"status": "accepted", "message": "Dataset registered successfully"}
        ), 201

    except globus_sdk.GlobusAPIError as e:
        logger.error(f"Globus API error: {e}")
        return jsonify({"error": str(e)}), e.http_status
    except Exception as e:
        logger.error(f"Error registering dataset: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/datasets", methods=["GET"])
@authenticated
def list_registered_datasets():
    """Fetch all datasets registered by user plus diamond-owned (public) datasets."""
    try:
        identity_id = request.cookies.get("primary_identity")
        if not identity_id:
            return jsonify({"error": "No identity ID found"}), 400

        datasets = g_database.get_datasets(identity_id)

        # Format datasets for JSON response
        datasets_data = []
        for dataset in datasets:
            datasets_data.append(
                {
                    "id": dataset.id,
                    "collection_uuid": dataset.collection_uuid,
                    "globus_path": dataset.globus_path,
                    "system_path": dataset.system_path,
                    "public": dataset.public,
                    "machine_name": dataset.machine_name,
                    "dataset_name": dataset.dataset_name,
                    "dataset_metadata": dataset.dataset_metadata,
                }
            )

        return jsonify({"datasets": datasets_data}), 200

    except Exception as e:
        logger.error(f"Error fetching datasets: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/transfers", methods=["GET"])
@authenticated
def list_transfer_tasks():
    """List the authenticated user's current transfer tasks."""
    try:
        transfer_client = get_transfer_client(request)

        # Get current transfer tasks prefixed with "Diamond:" label
        tasks = []
        for task in transfer_client.task_list(
            filter="status:ACTIVE,INACTIVE,FAILED/label:~Diamond:*"
        ):
            tasks.append(task)

        logger.info(f"Found {len(tasks)} Diamond transfer tasks")
        return jsonify(tasks)

    except globus_sdk.GlobusAPIError as e:
        logger.error(f"Globus API error: {e}")
        return jsonify({"error": str(e)}), e.http_status
    except Exception as e:
        logger.error(f"Error listing active transfer tasks: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/transfers", methods=["POST"])
@authenticated
def initiate_transfer():
    """Initiate a Globus transfer between two endpoints on behalf of the authenticated user.

    Expected JSON body:
    {
        "source_endpoint": "source_endpoint_id",
        "destination_endpoint": "destination_endpoint_id",
        "source_path": "source_path",
        "destination_path": "destination_path",
        "label": "optional_label"
    }

    (Following the same format as the Globus Transfer API)
    """
    try:
        transfer_client = get_transfer_client(request)

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        required_fields = [
            "source_endpoint",
            "destination_endpoint",
            "source_path",
            "destination_path",
        ]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Get the user's identity ID from cookies
        identity_id = request.cookies.get("primary_identity")
        if not identity_id:
            return jsonify({"error": "No identity ID found in cookies"}), 400

        source, destination = data["source_endpoint"], data["destination_endpoint"]

        transfer_data = globus_sdk.TransferData(
            source_endpoint=source,
            destination_endpoint=destination,
            label=f"Diamond:{source}->{destination}",  # label task as diamond-related
        )
        transfer_data.add_item(
            source_path=data["source_path"], destination_path=data["destination_path"]
        )

        transfer_result = transfer_client.submit_transfer(transfer_data)

        return jsonify(
            {
                "message": "Transfer initiated successfully",
                "task_id": transfer_result["task_id"],
            }
        ), 200

    except globus_sdk.GlobusAPIError as e:
        logger.error(f"Globus API error: {str(e)}")
        return jsonify({"error": f"Globus API error: {str(e)}"}), e.http_status
    except Exception as e:
        logger.error(f"Error initiating transfer: {str(e)}")
        return jsonify({"error": f"Error initiating transfer: {str(e)}"}), 500


@app.route("/api/list_partitions", methods=["POST"])
@authenticated
def diamond_get_partitions():
    partition_list = g_database.get_partitions(
        identity_id=request.cookies.get("primary_identity"),
        endpoint_uuid=request.json.get("endpoint"),
    )
    return jsonify(partition_list)


@app.route("/api/list_accounts", methods=["POST"])
@authenticated
def diamond_get_accounts():
    account_list = g_database.get_accounts(
        identity_id=request.cookies.get("primary_identity"),
        endpoint_uuid=request.json.get("endpoint"),
    )
    return jsonify(account_list)


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
    create_apptainer_def_shell = ShellFunction(create_apptainer_def_script)
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
    container_builder_shell = ShellFunction(build_container_script)

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


@app.route("/api/get_containers", methods=["GET"])
@authenticated
def get_containers():
    identity_id = request.cookies.get("primary_identity")
    logger.info(f"Loading containers for identity_id: {identity_id}")
    containers = g_database.load_containers(identity_id=identity_id)
    containers_data = {}
    for container in containers:
        logger.info(f"container task_id: {container.container_task_id}")
        container_task_id = container.container_task_id
        name = container.name

        containers_data[name] = {
            "container_task_id": container_task_id,
            "status": "",
            "base_image": container.base_image,
            "location": container.location,
        }

    logger.info(f"container status is {containers_data}")
    return jsonify(containers_data)


@app.route("/api/delete_container", methods=["POST"])
@authenticated
def diamond_delete_container():
    container_id = request.json.get("containerId")
    g_database.delete_container(container_id)
    logger.info(f"container {container_id} deleted")
    return jsonify({"message": "Container deleted successfully"})


@app.route("/api/submit_task", methods=["POST"])
@authenticated
def diamond_endpoint_submit_job():
    endpoint_id = request.json.get("endpoint")
    task_name = request.json.get("taskName")
    partition = request.json.get("partition")
    account = request.json.get("account")
    reservation = request.json.get("reservation", "")
    container = request.json.get("container")
    task = request.json.get("task")
    num_of_nodes = request.json.get("num_of_nodes", "1")  # 1 node is a safe default
    time_duration = request.json.get("time_duration")
    # max_retries = request.json.get("max_retries", 3)  # Default to 3 retries
    identity_id = request.cookies.get("primary_identity")
    dataset_id = request.json.get("dataset_id")

    if not num_of_nodes:
        num_of_nodes = 1
    if task is None:
        task = ""
    if reservation and reservation != "":
        reservation = "--reservation=" + reservation

    container_path = g_database.get_container_path_by_name(container)
    if dataset_id:
        dataset_system_path = g_database.get_dataset_by_id(dataset_id).system_path
    else:
        dataset_system_path = ""

    logger.info(
        f"Submit task container path: {container_path + '/' + container + '.sif'}"
    )

    globus_compute_client = initialize_globus_compute_client()
    location = g_database.get_diamond_dir(
        endpoint_uuid=endpoint_id, identity_id=identity_id
    )
    stdout_path = location + "/logs" + "/" + task_name + ".stdout"
    stderr_path = location + "/logs" + "/" + task_name + ".stderr"

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
        container_module_command=container_module_command,
        dataset_system_path=dataset_system_path,
    )
    submit_task_shell = ShellFunction(submit_task_script)
    function_id = globus_compute_client.register_function(submit_task_shell)
    task_id = globus_compute_client.run(
        endpoint_id=endpoint_id,
        function_id=function_id,
    )
    # Wait for submit task to complete with timeout to prevent hanging indefinitely
    max_attempts = 5
    submit_result = None
    for _ in range(max_attempts):
        try:
            submit_result = globus_compute_client.get_result(task_id)
        except TaskPending:
            continue
        except Exception:
            logger.exception("Failed to fetch results for task_id: %s", task_id)
            return jsonify(
                {
                    "error": "Failed to submit job - could not fetch results from endpoint",
                    "task_id": task_id,
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

    # Parse SLURM job ID from output - currently only supporting SLURM-based systems
    match = re.search(r"Submitted batch job (\d+)", submit_result.stdout)
    if not match:
        logger.error(f"Could not parse job ID from stdout: {submit_result.stdout}")
        return jsonify(
            {
                "error": "Failed to submit job - could not parse job ID from SLURM output",
                "stdout": submit_result.stdout,
            }
        ), 500

    slurm_job_id = match.group(1)
    logger.info(f"SLURM job ID: {slurm_job_id}")

    g_database.save_task(
        task_id=task_id,
        batch_job_id=slurm_job_id,
        task_name=task_name,
        identity_id=identity_id,
        task_status="submitted",
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

    tasks = g_database.load_tasks(identity_id=identity_id)

    for task in tasks:
        task_id = task.task_id
        try:
            current_task = globus_compute_client.get_task(task_id)
        except Exception as e:
            logger.warning(f"Task {task_id} not found. Error: {e}")
            continue

        task.endpoint_id = current_task["details"]["endpoint_id"]
        task_status_func_id = globus_compute_client.register_function(get_task_status)
        task_status_task_id = globus_compute_client.run(
            endpoint_id=task.endpoint_id,
            function_id=task_status_func_id,
            task_name=task.task_name,
        )
        task_status_task_status = globus_compute_client.get_task(task_status_task_id)
        while task_status_task_status["pending"]:
            time.sleep(2)
            task_status_task_status = globus_compute_client.get_task(
                task_status_task_id
            )
            continue
        task_status = globus_compute_client.get_result(task_status_task_id).stdout
        if task_status == "":
            task.task_status = task.task_status
        else:
            task.task_status = task_status
        logger.info(task_status)

        g_database.update_task_status(task.task_id, task.task_status)

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
                "endpoint_id": (
                    task.endpoint_id if hasattr(task, "endpoint_id") else "N/A"
                ),
                "task_create_time": task.task_create_time,
            },
            "result": task.stdout_path,
        }
        for task in updated_tasks
    }

    logger.info(f"Updated task status response: {tasks_data}")
    return jsonify(tasks_data)


@app.route("/api/stats", methods=["GET"])
@authenticated
def diamond_get_stats():
    identity_id = request.cookies.get("primary_identity")
    stats = g_database.get_stats(identity_id=identity_id)
    return jsonify(stats)


@app.route("/api/delete_task", methods=["POST"])
@authenticated
def diamond_delete_task():
    task_id = request.json.get("taskId")
    g_database.delete_task(task_id)
    logger.info(f"task {task_id} deleted")
    return jsonify({"message": "Task deleted successfully"})


if __name__ == "__main__":
    app.run()
