import json
import logging
import time
from typing import Dict, List, Tuple

from globus_compute_sdk import Client as GlobusComputeClient
from globus_sdk import ComputeAPIError

from diamond_backend.app.database.data_manager import Database
from diamond_backend.app.utils.compute import (
    describe_task_owner,
    wait_for_compute_result,
)
from diamond_backend.app.utils.config_loader import load_partitions
from diamond_backend.app.utils.errors import ComputeTaskFailed, ComputeTaskTimeout
from diamond_backend.app.utils.functions import get_machine_metadata
from diamond_backend.app.utils.host_machine_mapping import resolve_host

_METADATA_SUBMIT_MAX_ATTEMPTS = 3
_METADATA_INITIAL_DELAY = 1.0
_METADATA_MAX_DELAY = 8.0
_RETRYABLE_COMPUTE_ERROR_CODES = {"RESOURCE_CONFLICT"}

logger = logging.getLogger(__name__)


MEP_DEFAULT_ENDPOINT_CONFIG = {
    # DELTA MEP
    "4a266c83-3c68-4a75-99b3-9c7459f2f7ef": {
        "account": "bcrc-delta-cpu",
        "exclusive": False,
        "partition": "cpu-interactive",
    },
    # ANVIL MEP
    "5aafb4c1-27b2-40d8-a038-a0277611868f": {
        "exclusive": False,
        "partition": "shared",
    },
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
    *,
    endpoint_name: str | None = None,
    username: str | None = None,
):
    """Wrapper over Globus compute clients run function.

    This method uses the create_batch method that allows passing
    user_endpoint_config for the MEP to interface with the batch system.
    endpoint_name and username only label the log line; see describe_task_owner.
    """
    logger.info(
        "Submitting task to endpoint %s (%s), user %s, with user_config: %s",
        endpoint_id,
        endpoint_name,
        username,
        user_endpoint_config,
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
    endpoint_name: str | None = None,
    username: str | None = None,
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
                endpoint_name=endpoint_name,
                username=username,
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


def endpoint_initialization_status(
    global_compute_client: GlobusComputeClient,
    identity_id: str,
    database: Database,
) -> dict[str, dict[str, str | bool]]:
    """This method returns a list of all endpoints and their current user selection state"""

    all_endpoints = global_compute_client.get_endpoints(role="any")
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


def register_endpoint(
    globus_compute_client: GlobusComputeClient,
    identity_id,
    endpoint_uuid,
    database,
    logger,
):
    """Save one endpoint for the user."""
    endpoint_status = globus_compute_client.get_endpoint_status(
        endpoint_uuid=endpoint_uuid
    )["status"]
    endpoint_metadata = globus_compute_client.get_endpoint_metadata(
        endpoint_uuid=endpoint_uuid
    )
    endpoint_name = endpoint_metadata["display_name"]
    logger.info(f"Saving endpoint: {endpoint_name} ({endpoint_status})")
    database.save_endpoint(
        identity_id=identity_id,
        endpoint_name=endpoint_name,
        endpoint_host=resolve_host(endpoint_metadata["hostname"]),
        endpoint_uuid=endpoint_uuid,
        endpoint_status=endpoint_status,
        # MEP specific hack
        user_endpoint_config=MEP_DEFAULT_ENDPOINT_CONFIG.get(endpoint_uuid),
    )


def refresh_managed_endpoints(
    globus_compute_client: GlobusComputeClient, identity_id, database, logger
):
    """Re-read the status of the user's managed endpoints from Globus Compute."""
    logger.info(f"Refreshing managed endpoints for user: {identity_id}")
    for endpoint in database.get_managed_endpoints(identity_id=identity_id):
        try:
            endpoint_status = globus_compute_client.get_endpoint_status(
                endpoint_uuid=endpoint.endpoint_uuid
            )["status"]
        except Exception as e:
            logger.error(
                f"Error getting endpoint status for endpoint {endpoint.endpoint_name}: {e}"
            )
            continue
        logger.info(f"Endpoint {endpoint.endpoint_name} status: {endpoint_status}")
        database.update_endpoint_status(
            identity_id=identity_id,
            endpoint_uuid=endpoint.endpoint_uuid,
            endpoint_status=endpoint_status,
        )


def _get_endpoint_machine_metadata(
    endpoint_uuid: str,
    globus_compute_client: GlobusComputeClient,
    metadata_func_id: str,
    logger: logging.Logger,
    user_endpoint_config: dict[str, str] | None,
    endpoint_name: str | None = None,
    username: str | None = None,
) -> Dict:
    """Get machine metadata for an endpoint"""
    metadata_task_id = _submit_metadata_task_with_retry(
        endpoint_uuid,
        globus_compute_client,
        metadata_func_id,
        logger,
        user_endpoint_config=user_endpoint_config,
        endpoint_name=endpoint_name,
        username=username,
    )
    if not metadata_task_id:
        return {}

    try:
        metadata_result = wait_for_compute_result(
            globus_compute_client,
            metadata_task_id,
            endpoint_uuid,
            logger,
            endpoint_name=endpoint_name,
            username=username,
        )
    except (ComputeTaskTimeout, ComputeTaskFailed):
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
    _, username = describe_task_owner(database, identity_id, endpoint_uuid)
    metadata = _get_endpoint_machine_metadata(
        endpoint_uuid,
        globus_compute_client,
        metadata_func_id,
        logger,
        user_endpoint_config,
        endpoint_name=endpoint_metadata.get("display_name"),
        username=username,
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
