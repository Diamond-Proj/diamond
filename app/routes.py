import time
from datetime import datetime

from flask import jsonify, redirect, request

from . import app, database, logger
from .utils.data_prep import parallel_load_endpoints_data, register_all_endpoints
from .utils.decorators import authenticated
from .utils.functions import (
    apptainer_def_file_creation,
    container_builder_wrapper_shell,
    get_container_status,
    get_task_status,
    log_reader_wrapper,
    submit_task,
)
from .utils.login_flow import initialize_globus_compute_client

HOST = app.config.get("HOST")
AUTH_URL = app.config.get("AUTH_URL")
NEXT_URL = app.config.get("NEXT_URL")

logger.info(f"HOST in routes.py: {HOST}")
logger.info(f"AUTH_URL in routes.py: {AUTH_URL}")
logger.info(f"NEXT_URL in routes.py: {NEXT_URL}")


@app.route("/api/home", methods=["GET"])
def home():
    """Home route."""
    logger.info(f"Home route redirecting to {NEXT_URL}/sign-in")
    return redirect(NEXT_URL + "/sign-in")


@app.route("/api/healthcheck", methods=["GET"])
def healthcheck():
    """Health check endpoint."""
    logger.info("Health check route")
    return (
        jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}),
        200,
    )


@app.route("/api/is_authenticated", methods=["GET"])
@authenticated
def is_authenticated():
    return jsonify({"is_authenticated": True})


@app.route("/api/data_prep", methods=["POST"])
def diamond_data_prep():
    globus_compute_client = initialize_globus_compute_client()
    identity_id = request.cookies.get("primary_identity")

    # Register endpoints and get all endpoints in one step
    all_endpoints = register_all_endpoints(
        globus_compute_client, identity_id, database, logger
    )
    active_endpoints = [endpoint for endpoint in all_endpoints if endpoint["endpoint_status"] == "online"]

    # Parallelize fetching partitions and accounts
    parallel_load_endpoints_data(
        active_endpoints, globus_compute_client, identity_id, database, logger
    )

    return jsonify({"status": "success", "endpoints": active_endpoints}), 200


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
    if reservation:
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
    identity_id = request.cookies.get("primary_identity")
    if not num_of_nodes:
        num_of_nodes = 1
    if task is None:
        task = ""
    if reservation:
        reservation = "--reservation=" + reservation

    container_path = database.get_container_path_by_name(container)
    logger.info(
        f"Submit task container path: {container_path + '/' + container + '.sif'}"
    )

    globus_compute_client = initialize_globus_compute_client()
    function_id = globus_compute_client.register_function(submit_task)
    sc_config_commands = ""
    if database.get_endpoint_host(endpoint_uuid=endpoint_id) == "tacc-frontera":
        sc_config_commands = "module load tacc-apptainer"
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
    # Wait for submit task to complete.
    submit_task_status = globus_compute_client.get_task(task_id)
    logger.info(f"submit_task_status: {submit_task_status}")
    logger.info(f"reservation: {reservation}")
    while submit_task_status["pending"]:
        logger.info("submit_task_status", submit_task_status)
        time.sleep(2)
        submit_task_status = globus_compute_client.get_task(task_id)
        continue

    database.save_task(
        task_id=task_id,
        task_name=task_name,
        identity_id=identity_id,
        task_status="submitted",
        task_create_time=datetime.now(),
        log_path=log_path,
    )
    return jsonify(
        {
            "task_id": task_id,
            "task_name": task_name,
            "message": "Task submitted successfully",
        }
    )


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
            task_name=task.task_name,
            identity_id=task.identity_id,
            task_status=task.task_status,
            task_create_time=task.task_create_time,
            log_path=task.log_path,
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
