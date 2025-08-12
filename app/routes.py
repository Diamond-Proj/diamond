import re
import time
from datetime import datetime

import globus_sdk
from flask import jsonify, redirect, request
from globus_compute_sdk.errors import TaskPending

from . import app, database, logger
from .utils.data_prep import load_accounts_partitions, register_all_endpoints
from .utils.decorators import authenticated
from .utils.functions import (
    apptainer_def_file_creation,
    container_builder_wrapper_shell,
    get_task_status,
    log_reader_wrapper,
    submit_task,
)
from .utils.login_flow import initialize_globus_compute_client
from .utils.transfer import get_transfer_client
from .utils.utils import get_git_info

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
        return jsonify({"status": "unhealthy", "timestamp": datetime.utcnow().isoformat(), "git": git_info}), 500
    else:
        return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "git": git_info}), 200
    

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
        globus_compute_client, identity_id, database, logger
    )
    return jsonify({"status": "success", "endpoints": all_endpoints}), 200


@app.route("/api/load_accounts_partitions", methods=["POST"])
@authenticated
def diamond_load_accounts_partitions():
    """Load accounts and partitions for an active endpoint"""
    identity_id = request.cookies.get("primary_identity")
    endpoint_uuid = request.json.get("endpoint_uuid")
    globus_compute_client = initialize_globus_compute_client()
    account_list, partition_list = load_accounts_partitions(endpoint_uuid, identity_id, database, logger, globus_compute_client)
    return jsonify({"status": "success", "account_list": account_list, "partition_list": partition_list}), 200


@app.route("/api/list_all_endpoints", methods=["GET"])
@authenticated
def diamond_list_all_endpoints():
    identity_id = request.cookies.get("primary_identity")
    all_endpoints = []
    for endpoint in database.get_endpoints(identity_id=identity_id):
        all_endpoints.append(
            {
                "endpoint_name": endpoint.endpoint_name,
                "endpoint_uuid": endpoint.endpoint_uuid,
                "endpoint_host": endpoint.endpoint_host,
                "endpoint_status": endpoint.endpoint_status,
            }
        )
    return all_endpoints


@app.route("/api/list_active_endpoints", methods=["GET"])
@authenticated
def diamond_list_active_endpoints():
    identity_id = request.cookies.get("primary_identity")
    active_endpoints = []
    for endpoint in database.get_endpoints(identity_id=identity_id):
        if endpoint.endpoint_status == "online":
            active_endpoints.append(
                {
                    "endpoint_name": endpoint.endpoint_name,
                    "endpoint_uuid": endpoint.endpoint_uuid,
                    "endpoint_host": endpoint.endpoint_host,
                    "endpoint_status": endpoint.endpoint_status,
                }
            )
        else:
            continue
    return active_endpoints


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
    partition_list = database.get_partitions(
        identity_id=request.cookies.get("primary_identity"),
        endpoint_uuid=request.json.get("endpoint"),
    )
    return jsonify(partition_list)


@app.route("/api/list_accounts", methods=["POST"])
@authenticated
def diamond_get_accounts():
    account_list = database.get_accounts(
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
    location = request.json.get("location")
    account = request.json.get("account")
    reservation = request.json.get("reservation")
    partition = request.json.get("partition")
    identity_id = request.cookies.get("primary_identity")

    logger.info(
        f""" Creating container with the following parameters:
        endpoint_id: {endpoint_id}
        container_name: {name}
        base_image: {base_image}
        dependencies: {dependencies}
        environment: {environment}
        commands: {commands}
        location: {location}
        account: {account}
        reservation: {reservation}
        partition: {partition}
        identity_id: {identity_id}"""
    )
    # First we create the def file using ShellFunction.
    globus_compute_client = initialize_globus_compute_client()
    def_file_creation_function_id = globus_compute_client.register_function(
        apptainer_def_file_creation
    )
    def_file_creation_task_id = globus_compute_client.run(
        endpoint_id=endpoint_id,
        base_image=base_image,
        location=location,
        dependencies=dependencies,
        commands=commands,
        environment=environment,
        function_id=def_file_creation_function_id,
        container_name=name,
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

    # Then we create the container using ShellFunction with SBATCH commands.
    sc_config_commands = ""
    if database.get_endpoint_host(endpoint_uuid=endpoint_id) == "tacc-frontera":
        sc_config_commands = "module load tacc-apptainer"
    if reservation and reservation != "":
        reservation = "--reservation=" + reservation
    function_id = globus_compute_client.register_function(
        container_builder_wrapper_shell
    )
    container_task_id = globus_compute_client.run(
        container_name=name,
        base_image=base_image,
        location=location,
        endpoint_id=endpoint_id,
        partition=partition,
        account=account,
        reservation=reservation,
        sc_config_commands=sc_config_commands,
        function_id=function_id,
    )

    database.save_container(
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
    log_file_path = request.args.get("log_path")
    endpoint_id = request.args.get("endpoint_id")
    build_task_id = request.args.get("task_id")  # Original build task ID
    log_task_id = request.args.get("log_task_id")  # Previous log reader task ID

    if not log_file_path or not endpoint_id:
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
            except:
                pass

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
    containers = database.load_containers(identity_id=identity_id)
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
    database.delete_container(container_id)
    logger.info(f"container {container_id} deleted")
    return jsonify({"message": "Container deleted successfully"})


@app.route("/api/submit_task", methods=["POST"])
@authenticated
def diamond_endpoint_submit_job():
    endpoint_id = request.json.get("endpoint")
    task_name = request.json.get("taskName")
    partition = request.json.get("partition")
    account = request.json.get("account")
    reservation = request.json.get("reservation")
    container = request.json.get("container")
    log_path = request.json.get("log_path")
    task = request.json.get("task")
    num_of_nodes = request.json.get("num_of_nodes")
    time_duration = request.json.get("time_duration")
    max_retries = request.json.get("max_retries", 3)  # Default to 3 retries
    identity_id = request.cookies.get("primary_identity")
    if not num_of_nodes:
        num_of_nodes = 1
    if task is None:
        task = ""
    if reservation and reservation != "":
        reservation = "--reservation=" + reservation

    container_path = database.get_container_path_by_name(container)
    logger.info(
        f"Submit task container path: {container_path + '/' + container + '.sif'}"
    )

    globus_compute_client = initialize_globus_compute_client()
    sc_config_commands = ""
    if database.get_endpoint_host(endpoint_uuid=endpoint_id) == "tacc-frontera":
        sc_config_commands = "module load tacc-apptainer"
    function_id = globus_compute_client.register_function(submit_task)
    # job_status_func_id = globus_compute_client.register_function(get_job_status)
    

    task_id = globus_compute_client.run(
        partition=partition,
        account=account,
        reservation=reservation,
        container=container_path + "/" + container + ".sif",
        container_path=container_path,
        task=task,
        log_path=log_path,
        num_of_nodes=num_of_nodes,
        time_duration=time_duration,
        task_name=task_name,
        endpoint_id=endpoint_id,
        sc_config_commands=sc_config_commands,
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
            return jsonify({
                "error": "Failed to submit job - could not fetch results from endpoint",
                "task_id": task_id
            }), 500
        else:
            break
    
    if submit_result is None:
        return jsonify({
            "error": "Failed to submit job - task timed out after maximum attempts",
            "task_id": task_id
        }), 500
    
    logger.debug(f"SUBMIT RESULT: {submit_result}")

    # Parse SLURM job ID from output - currently only supporting SLURM-based systems
    match = re.search(r"Submitted batch job (\d+)", submit_result.stdout)
    if not match:
        logger.error(f"Could not parse job ID from stdout: {submit_result.stdout}")
        return jsonify({
            "error": "Failed to submit job - could not parse job ID from SLURM output",
            "stdout": submit_result.stdout,
        }), 500

    slurm_job_id = match.group(1)
    logger.info(f"SLURM job ID: {slurm_job_id}")

    
    database.save_task(
        task_id=task_id,
        batch_job_id=slurm_job_id,
        task_name=task_name,
        identity_id=identity_id,
        task_status="submitted",
        task_create_time=datetime.now(),
        log_path=log_path,
        stdout_path="",  # Will be set by backend
        stderr_path="",  # Will be set by backend
        compute_endpoint_id=endpoint_id,
        checkpoint_path="",  # Will be set by backend
    )
    return jsonify({
        "task_id": task_id,
        "batch_job_id": slurm_job_id,
        "task_name": task_name,
        "message": "Task submitted successfully",
    })


@app.route("/api/get_task_status", methods=["GET"])
@authenticated
def diamond_get_task_status():
    identity_id = request.cookies.get("primary_identity")
    globus_compute_client = initialize_globus_compute_client()

    tasks = database.load_tasks(identity_id=identity_id)
    task_status_changed = False

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
            task_status_changed = True
        logger.info(task_status)

        database.save_task(
            task_id=task.task_id,
            batch_job_id=task.batch_job_id,
            task_name=task.task_name,
            identity_id=task.identity_id,
            task_status=task.task_status,
            task_create_time=task.task_create_time,
            log_path=task.log_path,
            stdout_path=task.stdout_path,
            stderr_path=task.stderr_path,
            compute_endpoint_id=task.compute_endpoint_id,
            checkpoint_path=task.checkpoint_path,
        )

    # Reload the updated tasks from the database
    updated_tasks = database.load_tasks(identity_id=identity_id)

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
            "result": task.log_path,
        }
        for task in updated_tasks
    }

    logger.info(f"Updated task status response: {tasks_data}")
    return jsonify(tasks_data)


@app.route("/api/delete_task", methods=["POST"])
@authenticated
def diamond_delete_task():
    task_id = request.json.get("taskId")
    database.delete_task(task_id)
    logger.info(f"task {task_id} deleted")
    return jsonify({"message": "Task deleted successfully"})


if __name__ == "__main__":
    app.run()
