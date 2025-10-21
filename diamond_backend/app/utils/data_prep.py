import concurrent.futures
import time

from globus_compute_sdk import Client as GlobusComputeClient

from diamond_backend.app.database.data_manager import Database
from diamond_backend.app.utils.functions import get_accounts, get_partitions
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


def _get_endpoint_partitions(
    endpoint_uuid, globus_compute_client, get_partitions_func_id, logger
):
    partitions_task_id = globus_compute_client.run(
        endpoint_id=endpoint_uuid,
        function_id=get_partitions_func_id,
    )
    partitions_task_status = globus_compute_client.get_task(partitions_task_id)
    while partitions_task_status["pending"]:
        time.sleep(2)
        partitions_task_status = globus_compute_client.get_task(partitions_task_id)
        continue
    partitions_result = globus_compute_client.get_result(partitions_task_id)
    partitions_output = partitions_result.stdout
    partition_list = [p for p in partitions_output.split("\n") if p]
    logger.info(f"Partitions output for {endpoint_uuid}: {partition_list}")
    return endpoint_uuid, partition_list


def _get_endpoint_accounts(
    endpoint_uuid, globus_compute_client, accounts_func_id, logger
):
    accounts_task_id = globus_compute_client.run(
        endpoint_id=endpoint_uuid,
        function_id=accounts_func_id,
    )
    accounts_task_status = globus_compute_client.get_task(accounts_task_id)
    while accounts_task_status["pending"]:
        time.sleep(2)
        accounts_task_status = globus_compute_client.get_task(accounts_task_id)
        continue
    accounts_result = globus_compute_client.get_result(accounts_task_id)
    accounts_output = accounts_result.stdout
    account_list = [a for a in accounts_output.split("\n") if a]
    logger.info(f"Accounts output for {endpoint_uuid}: {account_list}")
    return endpoint_uuid, account_list


def load_accounts_partitions(
    endpoint_uuid, identity_id, database, logger, globus_compute_client
):
    """Load accounts and partitions for an endpoint"""
    get_partitions_func_id = globus_compute_client.register_function(get_partitions)
    accounts_func_id = globus_compute_client.register_function(get_accounts)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Start account and partition tasks in parallel
        account_future = executor.submit(
            _get_endpoint_accounts,
            endpoint_uuid,
            globus_compute_client,
            accounts_func_id,
            logger,
        )

        partition_future = executor.submit(
            _get_endpoint_partitions,
            endpoint_uuid,
            globus_compute_client,
            get_partitions_func_id,
            logger,
        )

        # Process results as they complete
        partition_list = None
        account_list = None

        for future in concurrent.futures.as_completed(
            [partition_future, account_future]
        ):
            try:
                endpoint_uuid, result = future.result()
                if future == account_future:
                    account_list = result
                    database.save_accounts(
                        identity_id=identity_id,
                        endpoint_uuid=endpoint_uuid,
                        accounts=account_list,
                    )
                elif future == partition_future:
                    partition_list = result
                    database.save_partition(
                        identity_id=identity_id,
                        endpoint_uuid=endpoint_uuid,
                        partitions=partition_list,
                    )
                else:
                    logger.error(f"Unknown future: {future}")
            except Exception as e:
                logger.error(
                    f"Error processing endpoint data with endpoint_uuid: {endpoint_uuid}: {e}"
                )
                raise

    return account_list, partition_list
