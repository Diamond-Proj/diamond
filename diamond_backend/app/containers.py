import logging

from flask import jsonify, request

from diamond_backend.app import app, g_database
from diamond_backend.app.errors import RequestMalformed
from diamond_backend.app.task_runtime import refresh_identity_task_statuses
from diamond_backend.app.utils.decorators import authenticated

logger = logging.getLogger(__name__)


def _resolve_container_status(container, task_lookup=None):
    if not task_lookup or not getattr(container, "container_task_id", None):
        return container.container_status or ""

    linked_task = task_lookup.get(container.container_task_id)
    if not linked_task:
        return container.container_status or ""

    task_status = str(linked_task.task_status or "").strip().upper()
    if task_status in {"COMPLETED", "COMPLETING"}:
        return "ACTIVE"
    if task_status == "MISSING":
        return "FAILED"
    return task_status


def _serialize_containers(
    containers, current_identity=None, existing=None, task_lookup=None
):
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
            "status": _resolve_container_status(container, task_lookup),
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


@app.route("/api/get_all_containers", methods=["GET"])
@authenticated
def get_all_containers():
    identity_id = request.cookies.get("primary_identity")
    logger.info(f"Loading all containers for identity_id: {identity_id}")
    tasks = refresh_identity_task_statuses(identity_id)
    task_lookup = {task.task_id: task for task in tasks}
    containers = g_database.load_containers(identity_id=identity_id)
    containers_data = _serialize_containers(
        containers,
        current_identity=identity_id,
        task_lookup=task_lookup,
    )

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
    tasks = refresh_identity_task_statuses(identity_id)
    task_lookup = {task.task_id: task for task in tasks}
    containers = g_database.load_containers_by_endpoint(
        identity_id=identity_id, endpoint_uuid=endpoint_uuid
    )
    containers_data = _serialize_containers(
        containers,
        current_identity=identity_id,
        task_lookup=task_lookup,
    )

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
