import logging
import os

from flask import jsonify, request

from diamond_backend.app import app, g_database, g_runtime_redis
from diamond_backend.app.errors import RequestMalformed
from diamond_backend.app.utils.data_prep import globus_compute_wrapped_run
from diamond_backend.app.utils.decorators import authenticated
from diamond_backend.app.utils.functions import fetch_task_status
from diamond_backend.app.utils.login_flow import initialize_globus_compute_client

logger = logging.getLogger(__name__)

GET_CONTAINER_STATUS_DTASK_TYPE = "fetch_container_status"
GET_CONTAINER_STATUS_REDIS_TTL_SECONDS = 30
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
TERMINAL_STATES = {"COMPLETED", "COMPLETING", "FAILED", "MISSING"}


def _is_trackable_batch_job_id(batch_job_id):
    normalized = str(batch_job_id or "").strip()
    return bool(normalized and normalized.isdigit())


def _refresh_container_statuses(identity_id, containers):
    globus_compute_client = initialize_globus_compute_client()
    redis_key = f"dtask:{identity_id}:{GET_CONTAINER_STATUS_DTASK_TYPE}"
    runtime_record = g_runtime_redis.get(redis_key)

    if runtime_record is None:
        fetch_status_func_id = globus_compute_client.register_function(
            fetch_task_status
        )
        task_records = []
        filtered_containers = [
            container
            for container in containers
            if (container.container_status or "").upper() not in TERMINAL_STATES
            and _is_trackable_batch_job_id(container.container_task_id)
            and getattr(container, "endpoint_id", None)
        ]

        for container in filtered_containers:
            user_endpoint_config = g_database.get_endpoint_user_config(
                identity_id=identity_id, endpoint_uuid=container.endpoint_id
            )
            try:
                container_status_task_id = globus_compute_wrapped_run(
                    globus_compute_client,
                    endpoint_id=container.endpoint_id,
                    function_id=fetch_status_func_id,
                    user_endpoint_config=user_endpoint_config,
                    kwargs={"batch_job_id": str(container.container_task_id).strip()},
                )
            except Exception as e:
                logger.warning(
                    "Failed to submit fetch_task_status for container %s. Error: %s",
                    container.name,
                    e,
                )
                continue

            task_records.append(
                {
                    "identity_id": identity_id,
                    "dtask_type": GET_CONTAINER_STATUS_DTASK_TYPE,
                    "container_name": container.name,
                    "container_status_task_id": container_status_task_id,
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
        container_status_task_id = task_record["container_status_task_id"]
        try:
            container_status_task = globus_compute_client.get_task(
                container_status_task_id
            )
        except Exception as e:
            logger.warning(
                "Failed to load container status task %s. Error: %s",
                container_status_task_id,
                e,
            )
            continue

        if container_status_task.get("pending", False):
            pending_task_records.append(task_record)
            continue

        try:
            container_status_result = globus_compute_client.get_result(
                container_status_task_id
            )
        except Exception as e:
            logger.warning(
                "Failed to fetch result for container status task %s. Error: %s",
                container_status_task_id,
                e,
            )
            continue

        task_status = getattr(container_status_result, "stdout", "").strip()
        new_container_status = None
        if task_status:
            new_container_status = SLURM_STATE_MAPPING.get(task_status, "MISSING")
        else:
            container_record = g_database.get_container_by_name(
                task_record["container_name"]
            )
            previous_status = (
                getattr(container_record, "container_status", "")
                if container_record
                else ""
            )
            if previous_status in ["RUNNING", "COMPLETING"]:
                new_container_status = "COMPLETED"

        if new_container_status:
            try:
                g_database.update_container_status_by_name(
                    task_record["container_name"], new_container_status
                )
            except Exception:
                logger.exception(
                    "Failed to update container:%s", task_record["container_name"]
                )

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

        location = getattr(container, "location", "") or ""
        stdout_path = (
            os.path.join(location, "logs", f"{container.name}.stdout")
            if location
            else ""
        )
        stderr_path = (
            os.path.join(location, "logs", f"{container.name}.stderr")
            if location
            else ""
        )

        containers_data[container.name] = {
            "container_task_id": container.container_task_id,
            "status": container.container_status or "",
            "base_image": container.base_image,
            "location": container.location,
            "endpoint_id": endpoint_uuid or "",
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
            "host_name": host_name,
            "is_public": bool(getattr(container, "is_public", False)),
            "owner_identity_id": getattr(container, "identity_id", None),
            "is_owner": (
                current_identity is not None
                and container.identity_id == current_identity
            ),
        }
    return containers_data


@app.route("/api/get_all_containers", methods=["GET"])
@authenticated
def get_all_containers():
    identity_id = request.cookies.get("primary_identity")
    logger.info(f"Loading all containers for identity_id: {identity_id}")
    containers = g_database.load_containers(identity_id=identity_id)
    try:
        _refresh_container_statuses(identity_id=identity_id, containers=containers)
    except Exception:
        logger.exception(
            "Failed to refresh container statuses for identity_id=%s", identity_id
        )
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

    logger.info(
        f"Loading containers for identity_id: {identity_id} on endpoint: {endpoint_uuid}"
    )
    containers = g_database.load_containers_by_endpoint(
        identity_id=identity_id, endpoint_uuid=endpoint_uuid
    )
    try:
        _refresh_container_statuses(identity_id=identity_id, containers=containers)
    except Exception:
        logger.exception(
            "Failed to refresh container statuses for identity_id=%s endpoint=%s",
            identity_id,
            endpoint_uuid,
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
