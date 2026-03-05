import json
import logging
import time
from typing import Dict, List, Tuple

from globus_compute_sdk import Client as GlobusComputeClient
from globus_compute_sdk.errors import TaskPending
from globus_sdk import ComputeAPIError

from diamond_backend.app.database.data_manager import Database
from diamond_backend.app.utils.config_loader import load_partitions
from diamond_backend.app.utils.functions import get_machine_metadata
from diamond_backend.app.utils.host_machine_mapping import resolve_host

_METADATA_SUBMIT_MAX_ATTEMPTS = 3
_METADATA_POLL_MAX_ATTEMPTS = 15
_METADATA_INITIAL_DELAY = 1.0
_METADATA_MAX_DELAY = 8.0
_RETRYABLE_COMPUTE_ERROR_CODES = {"RESOURCE_CONFLICT"}

logger = logging.getLogger(__name__)


DELTA_MEP_STATUS = {
    "uuid": "44a4297d-d07d-41a8-8ce9-c89464b23330",
    "name": "NCSA Delta Multi-User Endpoint",
    "display_name": "NCSA Delta Multi-User Endpoint",
    "owner": "18096de1-8571-4a48-9b30-4968b1d5a81b",
}

DELTA_USER_ENDPOINT_CONFIG = {
    "account": "bcrc-delta-cpu",
    "exclusive": False,
    "partition": "cpu-interactive",
}


def _is_retryable_compute_error(error: ComputeAPIError) -> bool:
    """Return True if Globus Compute error is safe to retry."""
    code = getattr(error, "code", None)
    status = getattr(error, "http_status", None)
    return (code and code in _RETRYABLE_COMPUTE_ERROR_CODES) or status == 409


def globus_compute_wrapped_run(
    globus_compute_client: GlobusComputeClient,
    endpoint_id: str,
    function_id: str,
    user_endpoint_config: Dict[str, str] | None = None,
    args: tuple | None = None,
    kwargs: dict | None = None,
):
    """Wrapper over Globus compute clients run function.

    This method uses the create_batch method that allows passing
    user_endpoint_config for the MEP to interface with the batch system
    """
    logger.info(
        "Submitting task with user_config:{} to ep:{}".format(
            user_endpoint_config, endpoint_id
        )
    )
    batch = globus_compute_client.create_batch(
        user_endpoint_config=user_endpoint_config
    )
    batch.add(function_id, args=args, kwargs=kwargs)
    r = globus_compute_client.batch_run(endpoint_id, batch)
    return r["tasks"][function_id][0]


def _submit_metadata_task_with_retry(
    endpoint_uuid: str,
    globus_compute_client: GlobusComputeClient,
    metadata_func_id: str,
    logger: logging.Logger,
    max_attempts: int = _METADATA_SUBMIT_MAX_ATTEMPTS,
    user_endpoint_config: Dict[str, str] | None = None,
) -> str | None:
    """Submit the metadata task, retrying transient Compute errors."""
    delay = _METADATA_INITIAL_DELAY
    for attempt in range(1, max_attempts + 1):
        try:
            return globus_compute_wrapped_run(
                globus_compute_client,
                endpoint_id=endpoint_uuid,
                function_id=metadata_func_id,
                user_endpoint_config=user_endpoint_config,
            )
        except ComputeAPIError as exc:
            if not _is_retryable_compute_error(exc) or attempt == max_attempts:
                logger.error(
                    "Error running metadata function for endpoint %s: %s",
                    endpoint_uuid,
                    exc,
                )
                return None

            logger.warning(
                "Metadata function submission conflict for %s (attempt %s/%s). "
                "Retrying in %.1fs.",
                endpoint_uuid,
                attempt,
                max_attempts,
                delay,
            )
            time.sleep(delay)
            delay = min(delay * 2, _METADATA_MAX_DELAY)
    return None


def _wait_for_metadata_result(
    globus_compute_client: GlobusComputeClient,
    metadata_task_id: str,
    logger: logging.Logger,
    max_attempts: int = _METADATA_POLL_MAX_ATTEMPTS,
) -> object | None:
    """Poll Globus Compute for the metadata task result."""
    delay = _METADATA_INITIAL_DELAY
    for attempt in range(1, max_attempts + 1):
        try:
            return globus_compute_client.get_result(metadata_task_id)
        except TaskPending:
            logger.info(
                "Metadata task %s still pending (attempt %s/%s).",
                metadata_task_id,
                attempt,
                max_attempts,
            )
            time.sleep(delay)
            delay = min(delay * 1.5, _METADATA_MAX_DELAY)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(
                "Unexpected error retrieving metadata for task %s: %s",
                metadata_task_id,
                exc,
            )
            return None

    logger.error(
        "Metadata task %s pending after %s attempts; giving up.",
        metadata_task_id,
        max_attempts,
    )
    return None


def endpoint_initialization_status(
    global_compute_client: GlobusComputeClient,
    identity_id: str,
    database: Database,
) -> dict[str, dict[str, str | bool]]:
    """This method returns a list of all endpoints and their current user selection state"""

    all_endpoints = global_compute_client.get_endpoints(role="any")
    all_endpoints.append(DELTA_MEP_STATUS)
    endpoints_in_db = database.get_endpoints(identity_id=identity_id)

    endpoint_map = {}
    for endpoint in all_endpoints:
        endpoint_map[endpoint["uuid"]] = {
            "name": endpoint["display_name"],
            "is_managed": False,
        }

    for endpoint in endpoints_in_db:
        if endpoint.endpoint_uuid in endpoint_map:
            endpoint_map[endpoint.endpoint_uuid]["is_managed"] = endpoint.is_managed

    return endpoint_map


def register_all_endpoints(
    globus_compute_client: GlobusComputeClient, identity_id, database, logger
):
    logger.info(f"Registering all endpoints for user: {identity_id}")

    # Specify role=Any to fetch MEPs in addition to those owned by the user
    endpoints = globus_compute_client.get_endpoints(role="any")
    # Add DELTA MEP that's not public
    endpoints.append(DELTA_MEP_STATUS)
    all_endpoints = []
    for endpoint in endpoints:
        logger.info(f"Checking endpoint: {endpoint}")
        endpoint_name = endpoint["display_name"]
        endpoint_uuid = endpoint["uuid"]
        try:
            endpoint_status = globus_compute_client.get_endpoint_status(
                endpoint_uuid=endpoint_uuid
            )["status"]
            logger.info(f"Endpoint {endpoint_name} status: {endpoint_status}")
        except Exception as e:
            logger.error(
                f"Error getting endpoint status for endpoint {endpoint_name}: {e}"
            )
            continue
        endpoint_metadata = globus_compute_client.get_endpoint_metadata(
            endpoint_uuid=endpoint_uuid
        )
        endpoint_host = resolve_host(endpoint_metadata["hostname"])
        if not database.exists_endpoint(
            identity_id=identity_id, endpoint_uuid=endpoint_uuid
        ):
            logger.info(f"Saving endpoint: {endpoint_name}")
            user_endpoint_config = None
            # Delta MEP specific hack
            if endpoint_uuid == "44a4297d-d07d-41a8-8ce9-c89464b23330":
                user_endpoint_config = DELTA_USER_ENDPOINT_CONFIG
            database.save_endpoint(
                identity_id=identity_id,
                endpoint_name=endpoint_name,
                endpoint_host=endpoint_host,
                endpoint_uuid=endpoint_uuid,
                endpoint_status=endpoint_status,
                user_endpoint_config=user_endpoint_config,
            )
        else:
            logger.info(f"Endpoint {endpoint_name} already exists, updating status")
            database.update_endpoint_status(
                endpoint_uuid=endpoint_uuid, endpoint_status=endpoint_status
            )
        all_endpoints.append(
            {
                "endpoint_uuid": endpoint_uuid,
                "endpoint_name": endpoint_name,
                "endpoint_host": endpoint_host,
                "endpoint_status": endpoint_status,
            }
        )
    return all_endpoints


def _get_endpoint_machine_metadata(
    endpoint_uuid: str,
    globus_compute_client: GlobusComputeClient,
    metadata_func_id: str,
    logger: logging.Logger,
    user_endpoint_config: dict[str, str] | None,
) -> Dict:
    """Get machine metadata for an endpoint"""
    metadata_task_id = _submit_metadata_task_with_retry(
        endpoint_uuid,
        globus_compute_client,
        metadata_func_id,
        logger,
        user_endpoint_config=user_endpoint_config,
    )
    if not metadata_task_id:
        return {}

    metadata_result = _wait_for_metadata_result(
        globus_compute_client,
        metadata_task_id,
        logger,
    )
    if metadata_result is None:
        return {}

    metadata_output = getattr(metadata_result, "stdout", None)
    if not metadata_output and metadata_result not in (None, ""):
        metadata_output = str(metadata_result)

    if not metadata_output:
        logger.error(f"No metadata output returned for endpoint {endpoint_uuid}")
        return {}

    try:
        metadata = json.loads(metadata_output)
    except json.JSONDecodeError as exc:
        logger.error(
            f"Unable to decode metadata for endpoint {endpoint_uuid}: {exc}. "
            f"Raw output: {metadata_output}"
        )
        raise

    logger.info(f"Metadata output for {endpoint_uuid}: {metadata}")
    return metadata


def _get_partitions_from_config(
    endpoint_uuid: str,
    endpoint_metadata: Dict,
    logger: logging.Logger,
) -> List[str] | None:
    """Try to get partitions from config file first"""
    try:
        endpoint_host = resolve_host(endpoint_metadata["hostname"])
        if endpoint_host == "unknown":
            logger.info(f"Unknown host for endpoint {endpoint_uuid}, cannot use config")
            return None

        partitions = load_partitions(endpoint_host)
        # TODO: add partitions to all supported machines
        logger.info(f"Found partitions in config for {endpoint_host}: {partitions}")
        return partitions
    except Exception as e:
        logger.warning(
            f"Error loading partitions from config for endpoint {endpoint_uuid}: {e}"
        )
        return None


def load_accounts_partitions(
    endpoint_uuid: str,
    identity_id: str,
    database: Database,
    logger: logging.Logger,
    globus_compute_client: GlobusComputeClient,
) -> Tuple[List[str], List[str]]:
    """Load accounts and partitions for an endpoint"""
    try:
        endpoint_metadata = globus_compute_client.get_endpoint_metadata(
            endpoint_uuid=endpoint_uuid
        )
    except ComputeAPIError as e:
        logger.error(f"Error getting endpoint metadata for {endpoint_uuid}: {e}")
        return [], []

    configured_partitions = _get_partitions_from_config(
        endpoint_uuid,
        endpoint_metadata,
        logger,
    )

    user_endpoint_config = database.get_endpoint_user_config(
        identity_id=identity_id, endpoint_uuid=endpoint_uuid
    )
    metadata_func_id = globus_compute_client.register_function(get_machine_metadata)
    metadata = _get_endpoint_machine_metadata(
        endpoint_uuid,
        globus_compute_client,
        metadata_func_id,
        logger,
        user_endpoint_config,
    )

    account_list = metadata.get("accounts", []) if metadata else []
    partition_list = (
        configured_partitions
        if configured_partitions
        else metadata.get("partitions", [])
    )

    if metadata:
        if metadata.get("accounts_error"):
            logger.warning(
                f"Accounts retrieval reported error for {endpoint_uuid}: "
                f"{metadata['accounts_error']}"
            )
        if not configured_partitions and metadata.get("partition_error"):
            logger.warning(
                f"Partition retrieval reported error for {endpoint_uuid}: "
                f"{metadata['partition_error']}"
            )

    if account_list:
        database.save_accounts(
            identity_id=identity_id,
            endpoint_uuid=endpoint_uuid,
            accounts=account_list,
        )
    else:
        logger.warning(f"No accounts retrieved for endpoint {endpoint_uuid}")

    if partition_list:
        logger.info(f"Using partitions for endpoint {endpoint_uuid}: {partition_list}")
        database.save_partition(
            identity_id=identity_id,
            endpoint_uuid=endpoint_uuid,
            partitions=partition_list,
        )
    else:
        logger.warning(f"No partitions available for endpoint {endpoint_uuid}")

    return account_list, partition_list
