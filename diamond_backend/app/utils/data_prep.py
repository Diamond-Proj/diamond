import json
import logging
import time
from typing import Dict, List, Tuple

from globus_compute_sdk import Client as GlobusComputeClient
from globus_sdk import ComputeAPIError

from diamond_backend.app.database.data_manager import Database
from diamond_backend.app.utils.config_loader import load_partitions
from diamond_backend.app.utils.functions import get_machine_metadata
from diamond_backend.app.utils.host_machine_mapping import resolve_host


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


def register_all_endpoints(
    globus_compute_client: GlobusComputeClient, identity_id, database, logger
):
    logger.info(f"Registering all endpoints for user: {identity_id}")

    # Specify role=Any to fetch MEPs in addition to those owned by the user
    endpoints = globus_compute_client.get_endpoints(role="any")
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
            database.save_endpoint(
                identity_id=identity_id,
                endpoint_name=endpoint_name,
                endpoint_host=endpoint_host,
                endpoint_uuid=endpoint_uuid,
                endpoint_status=endpoint_status,
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
) -> Dict:
    """Get machine metadata for an endpoint"""
    try:
        metadata_task_id = globus_compute_client.run(
            endpoint_id=endpoint_uuid,
            function_id=metadata_func_id,
        )
    except ComputeAPIError as e:
        logger.error(
            f"Error running metadata function for endpoint {endpoint_uuid}: {e}"
        )
        return {}

    metadata_task_status = globus_compute_client.get_task(metadata_task_id)
    for _ in range(10):
        if metadata_task_status["pending"]:
            time.sleep(2)
            metadata_task_status = globus_compute_client.get_task(metadata_task_id)
        else:
            break
    metadata_result = globus_compute_client.get_result(metadata_task_id)
    metadata_output = metadata_result.stdout

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

    metadata_func_id = globus_compute_client.register_function(get_machine_metadata)
    metadata = _get_endpoint_machine_metadata(
        endpoint_uuid,
        globus_compute_client,
        metadata_func_id,
        logger,
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
