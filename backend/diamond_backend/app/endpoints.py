import logging
import os

from flask import jsonify, request

from diamond_backend.app import app, g_database
from diamond_backend.app.errors import RequestMalformed
from diamond_backend.app.task_runtime import (
    TaskSubmissionError,
    _wait_for_compute_result,
)
from diamond_backend.app.utils.config_loader import load_partitions
from diamond_backend.app.utils.data_prep import (
    endpoint_initialization_status,
    globus_compute_wrapped_run,
    load_accounts_partitions,
    refresh_managed_endpoints,
    register_endpoint,
)
from diamond_backend.app.utils.decorators import authenticated
from diamond_backend.app.utils.functions import (
    check_diamond_work_path,
    create_diamond_dir,
)
from diamond_backend.app.utils.login_flow import initialize_globus_compute_client

logger = logging.getLogger(__name__)


@app.route("/api/refresh_managed_endpoints", methods=["POST"])
@authenticated
def diamond_refresh_managed_endpoints():
    """Refresh the status of the user's managed endpoints"""
    identity_id = request.cookies.get("primary_identity")
    globus_compute_client = initialize_globus_compute_client()
    refresh_managed_endpoints(globus_compute_client, identity_id, g_database, logger)
    return jsonify({"status": "success"}), 200


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


@app.route("/api/set_diamond_work_path", methods=["POST"])
@authenticated
def diamond_set_diamond_work_path():
    identity_id = request.cookies.get("primary_identity")
    endpoint_uuid = request.json.get("endpoint_uuid")
    diamond_work_path = str(request.json.get("diamond_work_path") or "").strip()

    globus_compute_client = initialize_globus_compute_client()
    user_endpoint_config = g_database.get_endpoint_user_config(
        identity_id=identity_id, endpoint_uuid=endpoint_uuid
    )

    def run_on_endpoint(shell_function, kwargs):
        function_id = globus_compute_client.register_function(shell_function)
        task_id = globus_compute_wrapped_run(
            globus_compute_client,
            endpoint_id=endpoint_uuid,
            function_id=function_id,
            user_endpoint_config=user_endpoint_config,
            kwargs=kwargs,
        )
        return _wait_for_compute_result(globus_compute_client, task_id)

    try:
        # The endpoint expands ~/$HOME and prints the canonical directory, or 0
        # when it is missing or not writable.
        check_result = run_on_endpoint(
            check_diamond_work_path, {"diamond_work_path": diamond_work_path}
        )
        resolved_base = check_result.stdout.strip()
        if not resolved_base.startswith("/"):
            return jsonify(
                {"error": "Diamond work path does not exist or is not writable"}
            ), 400

        # A base that already is a "diamond" directory is used as-is.
        if os.path.basename(resolved_base) == "diamond":
            diamond_dir = resolved_base
        else:
            diamond_dir = os.path.join(resolved_base, "diamond")
        diamond_log_dir = os.path.join(diamond_dir, "logs")
        diamond_image_dir = os.path.join(diamond_dir, "images")

        create_result = run_on_endpoint(
            create_diamond_dir,
            {
                "diamond_dir": diamond_dir,
                "diamond_log_dir": diamond_log_dir,
                "diamond_image_dir": diamond_image_dir,
            },
        )
        if create_result.returncode != 0:
            return jsonify(
                {"error": f"Failed to create {diamond_dir}: {create_result.stderr}"}
            ), 400
    except TaskSubmissionError as exc:
        return jsonify(exc.to_response_payload()), exc.http_status

    g_database.save_diamond_dir(
        identity_id=identity_id,
        endpoint_uuid=endpoint_uuid,
        diamond_dir=diamond_dir,
    )
    return jsonify({"status": "success", "diamond_dir": diamond_dir})


@app.route("/api/endpoint_overview", methods=["GET"])
@authenticated
def get_endpoint_management_overview():
    """Returns a dict of all endpoints from Globus Compute API and internal DB
    Returns:
        Dict: {<endpoint_uuid>: {name: <ep_name>, is_managed: <bool>}, ...}
    """

    identity_id = request.cookies.get("primary_identity")
    globus_compute_client = initialize_globus_compute_client()
    logger.info(f"Endpoint management overview for {identity_id} requested")
    return endpoint_initialization_status(
        globus_compute_client, identity_id, g_database
    )


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
                "is_managed": endpoint.is_managed,
            }
        )

    sorted_endpoints = sorted(all_endpoints, key=lambda x: x["endpoint_name"])
    sorted_active_first_endpoints = sorted(
        sorted_endpoints, key=lambda x: x["endpoint_status"], reverse=True
    )
    return sorted_active_first_endpoints


@app.route("/api/list_active_managed_endpoints", methods=["GET"])
@authenticated
def diamond_list_active_managed_endpoints():
    identity_id = request.cookies.get("primary_identity")
    active_managed_endpoints = []
    for endpoint in g_database.get_managed_endpoints(identity_id=identity_id):
        if endpoint.endpoint_status == "online":
            active_managed_endpoints.append(
                {
                    "endpoint_name": endpoint.endpoint_name,
                    "endpoint_uuid": endpoint.endpoint_uuid,
                    "endpoint_host": endpoint.endpoint_host,
                    "endpoint_status": endpoint.endpoint_status,
                    "diamond_dir": endpoint.diamond_dir,
                    "is_managed": endpoint.is_managed,
                }
            )
        else:
            continue
    return active_managed_endpoints


@app.route("/api/get_diamond_dir", methods=["GET"])
@authenticated
def diamond_get_diamond_dir():
    identity_id = request.cookies.get("primary_identity")
    endpoint_uuid = request.args.get("endpoint_uuid")
    diamond_dir = g_database.get_diamond_dir(
        identity_id=identity_id, endpoint_uuid=endpoint_uuid
    )
    # An endpoint that was never configured stores "".
    return jsonify({"diamond_dir": diamond_dir or None})


@app.route("/api/list_partitions", methods=["POST"])
@authenticated
def diamond_get_partitions():
    # try to get the partitions from the config file, if not found, get from the database
    endpoint_host = g_database.get_endpoint_host(
        endpoint_uuid=request.json.get("endpoint")
    )
    partition_list = load_partitions(endpoint_host)
    if not partition_list:
        partition_list = g_database.get_partitions(
            identity_id=request.cookies.get("primary_identity"),
            endpoint_uuid=request.json.get("endpoint"),
        )
    return jsonify(partition_list)


@app.route("/api/manage_endpoint/<endpoint_uuid>", methods=["PUT"])
@authenticated
def update_endpoint_managed_status(endpoint_uuid: str):
    """Allows updating the is_managed status of specific endpoints

    Returns:
        {"message": <user_string>, "new_status": <bool>}
    """
    identity_id = request.cookies["primary_identity"]

    try:
        is_managed: bool = request.json["is_managed"]  # type: ignore[index]
        assert isinstance(is_managed, bool)
    except KeyError:
        raise RequestMalformed("Missing JSON field 'is_managed'")

    logger.info(f"Endpoint management update for {endpoint_uuid} requested")

    # The Available tab is built from the Globus Compute API, so a user who has
    # never clicked "Refresh Endpoints" has no rows in the DB yet.
    if not g_database.exists_endpoint(
        identity_id=identity_id, endpoint_uuid=endpoint_uuid
    ):
        register_endpoint(
            initialize_globus_compute_client(),
            identity_id,
            endpoint_uuid,
            g_database,
            logger,
        )

    g_database.update_endpoint_managed_status(
        identity_id=identity_id, endpoint_uuid=endpoint_uuid, is_managed=is_managed
    )

    g_database.set_profile_initialization_state(identity_id, initialized=True)

    return jsonify(
        {
            "message": f"Endpoint:{endpoint_uuid} managed status updated to {is_managed}",
            "new_status": is_managed,
        }
    )


@app.route("/api/user_endpoint_config/<endpoint_uuid>", methods=["GET"])
@authenticated
def get_endpoint_config(endpoint_uuid: str):
    """Returns user_endpoint_config for the endpoint"""
    identity_id = request.cookies.get("primary_identity")
    user_endpoint_config = g_database.get_endpoint_user_config(
        identity_id=identity_id,
        endpoint_uuid=endpoint_uuid,
    )
    return jsonify(
        {"endpoint_uuid": endpoint_uuid, "user_endpoint_config": user_endpoint_config}
    )


@app.route("/api/user_endpoint_config/<endpoint_uuid>", methods=["PUT"])
@authenticated
def update_endpoint_config(endpoint_uuid: str):
    identity_id = request.cookies.get("primary_identity")
    user_endpoint_config = request.json.get("user_endpoint_config")
    g_database.update_endpoint_user_config(
        identity_id=identity_id,
        endpoint_uuid=endpoint_uuid,
        user_endpoint_config=user_endpoint_config,
    )
    return jsonify(
        {
            "message": f"Endpoint:{endpoint_uuid} user config update",
            "user_endpoint_config": user_endpoint_config,
        }
    )
