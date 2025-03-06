import time
from datetime import datetime

from flask import jsonify, redirect, request

from . import app, database, logger
from .utils.decorators import authenticated
from .utils.functions import (
    apptainer_def_file_creation,
    container_builder_wrapper_shell,
    get_accounts,
    get_container_status,
    get_partitions,
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
    # log.info(f"cookies in backend: {request.cookies}")
    # log.info(f"session in backend: {session}")
    return jsonify({"is_authenticated": True})


@app.route("/api/list_active_endpoints", methods=["GET"])
@authenticated
def diamond_list_active_endpoints():
    globus_compute_client = initialize_globus_compute_client()
    active_endpoints = []
    endpoints = globus_compute_client.get_endpoints()
    for endpoint in endpoints:
        endpoint_uuid = endpoint["uuid"]
        try:
            endpoint_status = globus_compute_client.get_endpoint_status(
                endpoint_uuid=endpoint_uuid
            )["status"]
        except Exception as e:
            logger.error(
                f"Error getting endpoint status for endpoint {endpoint['name']}: {e}"
            )
            continue
        if endpoint_status == "online":
            active_endpoints.append(
                {"endpoint_name": endpoint["name"], "endpoint_uuid": endpoint_uuid}
            )
    logger.info(f"active_endpoints: {active_endpoints}")
    return active_endpoints


@app.route("/api/list_partitions", methods=["POST"])
@authenticated
def diamond_get_partitions():
    endpoint_id = request.json.get("endpoint")
    logger.info(f"partitions endpoint_id: {endpoint_id}")
    globus_compute_client = initialize_globus_compute_client()
    partitions_func_id = globus_compute_client.register_function(get_partitions)
    partitions_task_id = globus_compute_client.run(
        endpoint_id=endpoint_id,
        function_id=partitions_func_id,
    )
    partitions_task_status = globus_compute_client.get_task(partitions_task_id)
    while partitions_task_status["pending"]:
        time.sleep(2)
        partitions_task_status = globus_compute_client.get_task(partitions_task_id)
        continue
    partitions_result = globus_compute_client.get_result(partitions_task_id)
    partitions_output = partitions_result.stdout
    partition_list = partitions_output.split("\n")
    for partition in partition_list:
        if not partition:
            partition_list.remove(partition)
    logger.info(f"partitions: {partition_list}")
    return jsonify(partition_list)


@app.route("/api/list_accounts", methods=["POST"])
@authenticated
def diamond_get_accounts():
    endpoint_id = request.json.get("endpoint")
    logger.info(f"endpoint_id: {endpoint_id}")
    globus_compute_client = initialize_globus_compute_client()
    accounts_func_id = globus_compute_client.register_function(get_accounts)
    accounts_task_id = globus_compute_client.run(
        endpoint_id=endpoint_id,
        function_id=accounts_func_id,
    )
    accounts_task_status = globus_compute_client.get_task(accounts_task_id)
    while accounts_task_status["pending"]:
        time.sleep(2)
        accounts_task_status = globus_compute_client.get_task(accounts_task_id)
        continue
    accounts = globus_compute_client.get_result(accounts_task_id)
    accounts_output = accounts.stdout
    account_list = accounts_output.split("\n")
    for account in account_list:
        if not account:
            account_list.remove(account)
    logger.info(f"accounts: {account_list}")
    return jsonify(account_list)


@app.route("/api/image_builder", methods=["POST"])
@authenticated
def diamond_endpoint_image_builder():

    endpoint_id = request.json.get("endpoint")
    name = request.json.get("name")
    # name = f"image-{endpoint_id}-v{datetime.now().strftime('%Y%m%d%H%M%S')}"
    base_image = request.json.get("base_image")
    dependencies = request.json.get("dependencies")
    environment = request.json.get("environment")
    commands = request.json.get("commands")
    location = request.json.get("location")
    account = request.json.get("account")
    partitions = request.json.get("partition")
    identity_id = request.cookies.get("primary_identity")

    logger.info(f"endpoint_id: {endpoint_id}")
    logger.info(f"container_name: {name}")
    logger.info(f"base_image: {base_image}")
    logger.info(f"dependencies: {dependencies}")
    logger.info(f"environment: {environment}")
    logger.info(f"commands: {commands}")
    logger.info(f"location: {location}")
    logger.info(f"account: {account}")
    logger.info(f"partitions: {partitions}")
    logger.info(f"identity_id: {identity_id}")
    slurm_commands = f"""
#SBATCH --time=00:10:00
#SBATCH --ntasks-per-node=1
#SBATCH --exclusive
#SBATCH --partition={partitions}  
#SBATCH --account={account}
"""

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
    function_id = globus_compute_client.register_function(
        container_builder_wrapper_shell
    )
    container_task_id = globus_compute_client.run(
        container_name=name,
        base_image=base_image,
        location=location,
        endpoint_id=endpoint_id,
        function_id=function_id,
        slurm_commands=slurm_commands,
    )
    # Output is available at {location}/{base_image}_log.stdout
    # container_task_status = globus_compute_client.get_task(container_task_id)
    # print("container_builder_wrapper_shell" , container_task_status)
    # while (container_task_status["pending"]):
    #     print("container_builder_wrapper_shell" , container_task_status)
    #     time.sleep(10)
    #     container_task_status = globus_compute_client.get_task(container_task_id)
    #     continue

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
    globus_compute_client = initialize_globus_compute_client()
    containers = database.load_containers(identity_id=identity_id)
    containers_data = {}
    for container in containers:
        logger.info(f"container task_id: {container.container_task_id}")
        container_task_id = container.container_task_id
        name = container.name

        endpoint_id = container.endpoint_id
        container_status_func_id = globus_compute_client.register_function(
            get_container_status
        )
        container_status_task_id = globus_compute_client.run(
            endpoint_id=endpoint_id, function_id=container_status_func_id, name=name
        )
        container_status_task_status = globus_compute_client.get_task(
            container_status_task_id
        )
        while container_status_task_status["pending"]:
            time.sleep(2)
            container_status_task_status = globus_compute_client.get_task(
                container_status_task_id
            )
            continue
        container_status = globus_compute_client.get_result(
            container_status_task_id
        ).stdout
        logger.info(f"container_status: {container_status}")
        if container_status == "":
            container_status = container.container_status
        else:
            container_status = container_status
            database.update_container_status(container_task_id, container_status)

        containers_data[name] = {
            "container_task_id": container_task_id,
            "status": container_status,
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
    container = request.json.get("container")
    log_path = request.json.get("log_path")
    task = request.json.get("task")
    num_of_nodes = request.json.get("num_of_nodes")
    identity_id = request.cookies.get("primary_identity")
    if not num_of_nodes:
        num_of_nodes = 1
    if task is None:
        task = ""

    container_path = database.get_container_path_by_name(container)
    logger.info(
        f"Submit task container path: {container_path + '/' + container + '.sif'}"
    )

    globus_compute_client = initialize_globus_compute_client()
    # globus_compute_executor = GlobusComputeExecutor(client=globus_compute_client, endpoint_id=endpoint_id)

    function_id = globus_compute_client.register_function(submit_task)
    task_id = globus_compute_client.run(
        partition=partition,
        account=account,
        container=container_path + "/" + container + ".sif",
        container_path=container_path,
        task=task,
        log_path=log_path,
        num_of_nodes=num_of_nodes,
        task_name=task_name,
        endpoint_id=endpoint_id,
        function_id=function_id,
    )
    # Wait for submit task to complete.
    submit_task_status = globus_compute_client.get_task(task_id)
    logger.info(f"submit_task_status: {submit_task_status}")
    while submit_task_status["pending"]:
        logger.info("submit_task_status", submit_task_status)
        time.sleep(10)
        submit_task_status = globus_compute_client.get_task(task_id)
        continue

    # fu = globus_compute_executor.submit(
    #     submit_task,
    #     partition=partition,
    #     container=container_path + "/" + container + ".sif",
    #     task=task,
    #     log_path=log_path,
    #     num_of_nodes=num_of_nodes,
    #     task_name=task_name)

    # fu_stdout = fu.result().stdout

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
