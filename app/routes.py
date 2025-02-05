import logging
import os
import time
from datetime import datetime
from urllib.parse import urlparse

from flask import flash, jsonify, make_response, redirect, request, session, url_for
from globus_compute_sdk import Executor as GlobusComputeExecutor

from . import app, database
from .utils.decorators import authenticated
from .utils.functions import (
    apptainer_def_file_creation,
    container_builder_wrapper_shell,
    get_accounts,
    get_build_log,
    get_container_status,
    get_partitions,
    get_task_status,
    log_reader_wrapper,
    submit_task,
)
from .utils.login_flow import initialize_globus_compute_client
from .utils.utils import (
    generate_one_time_token,
    get_safe_redirect,
    load_portal_client,
    validate_one_time_token,
)

# create and configure logger
logging.basicConfig(
    level=logging.INFO,
    datefmt="%Y-%m-%dT%H:%M:%S",
    format="%(asctime)-15s.%(msecs)03dZ %(levelname)-7s : %(name)s - %(message)s",
)
# create log object with current module name
log = logging.getLogger(__name__)

HOST = app.config.get("HOST")
AUTH_URL = app.config.get("AUTH_URL")
NEXT_URL = app.config.get("NEXT_URL")
NODE_ENV = app.config.get("NODE_ENV")

log.info(f"HOST in routes.py: {HOST}")
log.info(f"AUTH_URL in routes.py: {AUTH_URL}")
log.info(f"NEXT_URL in routes.py: {NEXT_URL}")
log.info(f"NODE_ENV in routes.py: {NODE_ENV}")


@app.route("/api/home", methods=["GET"])
def home():
    """Home route."""
    log.info(f"Home route redirecting to {NEXT_URL}/sign-in")
    return redirect(NEXT_URL + "/sign-in")


@app.route("/api/healthcheck", methods=["GET"])
def healthcheck():
    """Health check endpoint."""
    log.info("Health check route")
    return (
        jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}),
        200,
    )


def initiate_auth_flow(signup=False):
    """Common logic for login/signup."""
    redirect_uri = request.host_url.rstrip("/")  # Remove trailing slash if present
    log.info(f"Auth request with redirect_uri: {redirect_uri}")

    # Always use production backend's authcallback URL as redirect_uri
    auth_redirect_uri = (
        f"{AUTH_URL}/authcallback"
        if AUTH_URL
        else url_for("authcallback", _external=True)
    )

    client = load_portal_client()
    client.oauth2_start_flow(
        auth_redirect_uri,
        refresh_tokens=True,
        requested_scopes=os.environ["USER_SCOPES"].split(),
    )

    # Store the source backend URL in state
    params = {"state": redirect_uri}
    if signup:
        params["signup"] = "1"

    auth_uri = client.oauth2_get_authorize_url(query_params=params)
    return redirect(auth_uri)


@app.route("/api/signup", methods=["GET"])
def signup():
    """Send the user to Globus Auth with signup=1."""
    return initiate_auth_flow(signup=True)


@app.route("/api/login", methods=["GET"])
def login():
    """Send the user to Globus Auth."""
    return initiate_auth_flow()


@app.route("/api/is_authenticated", methods=["GET"])
@authenticated
def is_authenticated():
    # log.info(f"cookies in backend: {request.cookies}")
    # log.info(f"session in backend: {session}")
    return jsonify({"is_authenticated": True})


@app.route("/api/logout", methods=["GET"])
@authenticated
def logout():
    """
    - Revoke the tokens with Globus Auth.
    - Destroy the session state.
    - Remove cookies containing 'tokens'.
    - Redirect the user to the Globus Auth logout page.
    """
    client = load_portal_client()

    # Revoke the tokens with Globus Auth
    for token, token_type in (
        (token_info[ty], ty)
        # get all of the token info dicts
        for token_info in session["tokens"].values()
        # cross product with the set of token types
        for ty in ("access_token", "refresh_token")
        # only where the relevant token is actually present
        if token_info[ty] is not None
    ):
        client.oauth2_revoke_token(token, body_params={"token_type_hint": token_type})

    # Destroy the session state
    session.clear()

    # Remove cookies containing 'tokens'
    response = make_response(redirect(url_for("home", _external=True)))
    response.delete_cookie("tokens")

    log.info(f"Session after clearing: {session}")

    redirect_uri = url_for("home", _external=True)

    ga_logout_url = []
    ga_logout_url.append(os.environ["GLOBUS_AUTH_LOGOUT_URI"])
    ga_logout_url.append("?client={}".format(os.environ["PORTAL_CLIENT_ID"]))
    ga_logout_url.append("&redirect_uri={}".format(redirect_uri))
    ga_logout_url.append("&redirect_name=Diamond Service")

    # Redirect the user to the Globus Auth logout page
    response.headers["Location"] = "".join(ga_logout_url)
    return response


@app.route("/api/profile", methods=["GET"])
@authenticated
def profile():
    """Get user profile information if needed."""
    identity_id = session.get("primary_identity")
    if not identity_id:
        return jsonify({"error": "No identity found"}), 401

    profile = database.load_profile(identity_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    return jsonify(
        {
            "name": profile.name,
            "email": profile.email,
            "institution": profile.institution,
            "primary_identity": identity_id,
        }
    )


@app.route("/api/authcallback", methods=["GET"])
def authcallback():
    """Handle the response from Globus Auth."""
    # If there's an error, redirect to sign-in
    if "error" in request.args:
        error_msg = request.args.get("error_description", request.args["error"])
        log.error(f"Globus Auth error: {error_msg}")
        return redirect(NEXT_URL + "/sign-in")

    try:
        # Exchange code for tokens first
        client = load_portal_client()
        tokens = client.oauth2_exchange_code_for_tokens(request.args.get("code"))

        id_token = tokens.decode_id_token()
        identity_id = id_token.get("primary_identity")

        if not identity_id:
            log.error("No identity_id in token")
            return redirect(NEXT_URL + "/sign-in")

        # Create/update profile
        database.save_profile(
            identity_id=identity_id,
            name=id_token.get("name"),
            email=id_token.get("email"),
            institution=id_token.get("organization"),
        )

        # Now check state to determine where to redirect
        source_backend = request.args.get("state")
        if source_backend:
            # If we have a source backend, generate token and redirect there
            auth_data = {
                "tokens": tokens.by_resource_server,
                "name": id_token.get("name"),
                "email": id_token.get("email"),
                "institution": id_token.get("organization"),
                "primary_username": id_token.get("preferred_username"),
                "primary_identity": identity_id,
            }

            one_time_token = generate_one_time_token(auth_data)
            return redirect(
                f"{source_backend}/api/auth/complete?token={one_time_token}"
            )
        else:
            # If no source backend (production), set cookies directly
            session.update(
                tokens=tokens.by_resource_server,
                is_authenticated=True,
                name=id_token.get("name"),
                email=id_token.get("email"),
                institution=id_token.get("organization"),
                primary_username=id_token.get("preferred_username"),
                primary_identity=identity_id,
            )

            response = make_response(redirect(NEXT_URL + "/sign-in"))

            # Set cookie options
            parsed_url = urlparse(request.host_url)
            is_localhost = parsed_url.hostname == "localhost"
            cookie_options = {
                "secure": not is_localhost,
                "samesite": "Lax",
                "path": "/",
                "domain": None if is_localhost else f".{parsed_url.hostname}",
                "httponly": False,
            }

            # Set cookies
            response.set_cookie("is_authenticated", "true", **cookie_options)
            response.set_cookie(
                "primary_username", session["primary_username"], **cookie_options
            )
            response.set_cookie(
                "primary_identity", session["primary_identity"], **cookie_options
            )
            response.set_cookie("name", session["name"], **cookie_options)
            response.set_cookie("email", session["email"], **cookie_options)
            response.set_cookie("institution", session["institution"], **cookie_options)
            response.set_cookie("tokens", str(session["tokens"]), **cookie_options)

            return response

    except Exception as e:
        log.error(f"Error in authcallback: {str(e)}")
        return redirect(NEXT_URL + "/sign-in")


@app.route("/api/loadprofile", methods=["GET"])
def loadprofile():
    """Deprecated: Profile is now handled during auth flow."""
    log.warning("Deprecated /api/loadprofile called")
    return redirect(NEXT_URL + "/profile")


@app.route("/api/list_active_endpoints", methods=["GET"])
@authenticated
def diamond_list_active_endpoints():
    globus_compute_client = initialize_globus_compute_client()
    active_endpoints = []
    endpoints = globus_compute_client.get_endpoints()
    for endpoint in endpoints:
        endpoint_uuid = endpoint["uuid"]
        endpoint_status = globus_compute_client.get_endpoint_status(
            endpoint_uuid=endpoint_uuid
        )["status"]
        if endpoint_status == "online":
            active_endpoints.append(
                {"endpoint_name": endpoint["name"], "endpoint_uuid": endpoint_uuid}
            )
    logging.info(active_endpoints)
    return active_endpoints


@app.route("/api/list_partitions", methods=["POST"])
@authenticated
def diamond_get_partitions():
    endpoint_id = request.json.get("endpoint")
    logging.info(f"endpoint_id: {endpoint_id}")
    globus_compute_client = initialize_globus_compute_client()
    globus_compute_executer = GlobusComputeExecutor(
        client=globus_compute_client, endpoint_id=endpoint_id
    )
    fu = globus_compute_executer.submit(get_partitions)
    partitions = fu.result().stdout
    partition_list = partitions.split("\n")
    for partition in partition_list:
        if not partition:
            partition_list.remove(partition)
    logging.info(f"partitions: {partition_list}")
    return jsonify(partition_list)


@app.route("/api/list_accounts", methods=["POST"])
@authenticated
def diamond_get_accounts():
    endpoint_id = request.json.get("endpoint")
    logging.info(f"endpoint_id: {endpoint_id}")
    globus_compute_client = initialize_globus_compute_client()
    globus_compute_executer = GlobusComputeExecutor(
        client=globus_compute_client, endpoint_id=endpoint_id
    )
    fu = globus_compute_executer.submit(get_accounts)
    accounts = fu.result().stdout
    account_list = accounts.split("\n")
    for account in account_list:
        if not account:
            account_list.remove(account)
    logging.info(f"accounts: {account_list}")
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

    logging.info(f"endpoint_id: {endpoint_id}")
    logging.info(f"container_name: {name}")
    logging.info(f"base_image: {base_image}")
    logging.info(f"dependencies: {dependencies}")
    logging.info(f"environment: {environment}")
    logging.info(f"commands: {commands}")
    logging.info(f"location: {location}")
    logging.info(f"account: {account}")
    logging.info(f"partitions: {partitions}")

    slurm_commands = f"""
#SBATCH --time=00:10:00
#SBATCH --ntasks-per-node=1
#SBATCH --exclusive
#SBATCH --partition={partitions}  
#SBATCH --account={account}
"""

    # use get_partitions Shell function.
    # Use a env to have the command to get user accounts in an hpc system . Eg "accounts" in Delta.
    # We need user input text input for accounts now.

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
        print("def_file_creation_task_id", def_file_creation_task_status)
        time.sleep(10)
        def_file_creation_task_status = globus_compute_client.get_task(
            def_file_creation_task_id
        )
        continue

    print("def_file_creation_task_id", def_file_creation_task_status)
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
        identity_id=session["primary_identity"],
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
            print(
                f"Registered log reader function: {get_build_log.log_reader_function_id}"
            )

        # Create new log reader task if no log_task_id
        if not log_task_id:
            log_task_id = globus_compute_client.run(
                endpoint_id=endpoint_id,
                function_id=get_build_log.log_reader_function_id,
                log_file_path=log_file_path,
            )
            print(f"Created new log reader task: {log_task_id}")

        # Get status of current log reader task
        log_task_status = globus_compute_client.get_task(log_task_id)
        print(f"Log task status: {log_task_status}")

        # Get log content if task completed
        log_result = None
        if log_task_status.get("status") == "success":
            try:
                log_result = globus_compute_client.get_result(log_task_id)
                print(f"Log result: {log_result}")

                # Create new task using the same function ID
                new_log_task_id = globus_compute_client.run(
                    endpoint_id=endpoint_id,
                    function_id=get_build_log.log_reader_function_id,
                    log_file_path=log_file_path,
                )
            except Exception as e:
                print(f"Error getting log result: {e}")
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
        logging.error(f"Error getting build log: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/get_containers", methods=["GET"])
@authenticated
def get_containers():
    globus_compute_client = initialize_globus_compute_client()

    containers = database.load_containers(identity_id=session["primary_identity"])
    containers_data = {}
    for container in containers:
        logging.info(f"container: {container.container_task_id}")
        container_task_id = container.container_task_id
        name = container.name

        endpoint_id = container.endpoint_id
        globus_compute_executer = GlobusComputeExecutor(
            client=globus_compute_client, endpoint_id=endpoint_id
        )
        fu = globus_compute_executer.submit(get_container_status, name=name)
        fu_stdout = fu.result().stdout
        if fu_stdout == "":
            container_status = container.container_status
        else:
            container_status = fu_stdout
            database.update_container_status(container_task_id, container_status)
        logging.info("***************************************")
        logging.info(fu_stdout)

        containers_data[name] = {
            "container_task_id": container_task_id,
            "status": container_status,
            "base_image": container.base_image,
            "location": container.location,
        }

    logging.info(f"container status is {containers_data}")
    return jsonify(containers_data)


@app.route("/api/delete_container", methods=["POST"])
@authenticated
def diamond_delete_container():
    container_id = request.json.get("containerId")
    database.delete_container(container_id)
    logging.info(f"container {container_id} deleted")
    return jsonify({"message": "Container deleted successfully"})


@app.route("/api/submit_task", methods=["POST"])
@authenticated
def diamond_endpoint_submit_job():
    endpoint_id = request.json.get("endpoint")
    task_name = request.json.get("taskName")
    partition = request.json.get("partition")
    container = request.json.get("container")
    log_path = request.json.get("log_path")
    task = request.json.get("task")
    num_of_nodes = request.json.get("num_of_nodes")
    if not num_of_nodes:
        num_of_nodes = 1

    container_path = database.get_container_path_by_name(container)

    globus_compute_client = initialize_globus_compute_client()
    # globus_compute_executor = GlobusComputeExecutor(client=globus_compute_client, endpoint_id=endpoint_id)

    function_id = globus_compute_client.register_function(submit_task)

    task_id = globus_compute_client.run(
        partition=partition,
        container=container_path + "/" + container + ".sif",
        task=task,
        log_path=log_path,
        num_of_nodes=num_of_nodes,
        task_name=task_name,
        endpoint_id=endpoint_id,
        function_id=function_id,
    )

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
        identity_id=session["primary_identity"],
        task_status="submitted",
        task_create_time=datetime.now(),
        log_path=log_path,
    )
    return jsonify({"message": "Task submitted successfully"})


@app.route("/api/get_task_status", methods=["GET"])
@authenticated
def diamond_get_task_status():
    global_compute_client = initialize_globus_compute_client()

    tasks = database.load_tasks(identity_id=session["primary_identity"])

    for task in tasks:
        task_id = task.task_id
        logging.info(f"Updating status for task ID: {task_id}")

        current_task = global_compute_client.get_task(task_id)

        task.endpoint_id = current_task["details"]["endpoint_id"]
        globus_compute_executor = GlobusComputeExecutor(
            client=global_compute_client, endpoint_id=task.endpoint_id
        )
        fu = globus_compute_executor.submit(get_task_status, task_name=task.task_name)
        fu_stdout = fu.result().stdout
        if fu_stdout == "":
            task.task_status = task.task_status
        else:
            task.task_status = fu_stdout
        logging.info("++++++++++++++++++++++++++++++++++++++++++")
        logging.info(fu_stdout)

        database.save_task(
            task_id=task.task_id,
            task_name=task.task_name,
            identity_id=task.identity_id,
            task_status=task.task_status,
            task_create_time=task.task_create_time,
            log_path=task.log_path,
        )

    # Reload the updated tasks from the database
    updated_tasks = database.load_tasks(identity_id=session["primary_identity"])

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

    logging.info(f"Updated task status response: {tasks_data}")
    return jsonify(tasks_data)


@app.route("/api/delete_task", methods=["POST"])
@authenticated
def diamond_delete_task():
    task_id = request.json.get("taskId")
    database.delete_task(task_id)
    logging.info(f"task {task_id} deleted")
    return jsonify({"message": "Task deleted successfully"})


@app.route("/api/auth/complete", methods=["GET"])
def auth_complete():
    """Handle auth completion and set cookies."""
    token = request.args.get("token")
    if not token:
        log.error("No token provided in auth completion")
        return redirect(NEXT_URL + "/sign-in")

    try:
        # Decode and validate the token
        auth_data = validate_one_time_token(token)

        # Update session
        session.update(
            tokens=auth_data["tokens"],
            is_authenticated=True,
            name=auth_data["name"],
            email=auth_data["email"],
            institution=auth_data["institution"],
            primary_username=auth_data["primary_username"],
            primary_identity=auth_data["primary_identity"],
        )

        # Create response
        response = make_response(redirect(NEXT_URL + "/sign-in"))

        # Set cookie options based on environment
        parsed_url = urlparse(request.host_url)
        is_localhost = parsed_url.hostname == "localhost"
        cookie_options = {
            "secure": not is_localhost,
            "samesite": "Lax",
            "path": "/",
            "domain": None if is_localhost else f".{parsed_url.hostname}",
            "httponly": False,
        }

        # Set cookies
        response.set_cookie("is_authenticated", "true", **cookie_options)
        response.set_cookie(
            "primary_username", session["primary_username"], **cookie_options
        )
        response.set_cookie(
            "primary_identity", session["primary_identity"], **cookie_options
        )
        response.set_cookie("name", session["name"], **cookie_options)
        response.set_cookie("email", session["email"], **cookie_options)
        response.set_cookie("institution", session["institution"], **cookie_options)
        response.set_cookie("tokens", str(session["tokens"]), **cookie_options)

        return response

    except Exception as e:
        log.error(f"Error processing auth completion: {str(e)}")
        return redirect(NEXT_URL + "/sign-in")


if __name__ == "__main__":
    app.run()
