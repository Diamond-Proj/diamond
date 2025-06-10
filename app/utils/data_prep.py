import concurrent.futures
import time

from .functions import get_accounts, get_partitions
from .parsers import resolve_host


def register_all_endpoints(globus_compute_client, identity_id, database, logger):
    logger.info(f"Registering all endpoints for user: {identity_id}")
    endpoints = globus_compute_client.get_endpoints() # get all endpoints owned by the user across all systems
    all_endpoints = []

    for endpoint in endpoints:
        logger.info(f"Checking endpoint: {endpoint}")
        endpoint_name = endpoint["name"]
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
        endpoint_metadata = globus_compute_client.get_endpoint_metadata(endpoint_uuid=endpoint_uuid)
        endpoint_host = resolve_host(endpoint_metadata["hostname"])
        if not database.exists_endpoint(endpoint_uuid=endpoint_uuid):
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
            database.update_endpoint_status(endpoint_uuid=endpoint_uuid, endpoint_status=endpoint_status)
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


def parallel_load_endpoints_data(
    active_endpoints, globus_compute_client, identity_id, database, logger
):
    """Load partitions and accounts for endpoints in parallel"""
    get_partitions_func_id = globus_compute_client.register_function(get_partitions)
    accounts_func_id = globus_compute_client.register_function(get_accounts)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Start partition and account tasks in parallel
        partition_futures = {
            executor.submit(
                _get_endpoint_partitions,
                endpoint["endpoint_uuid"],
                globus_compute_client,
                get_partitions_func_id,
                logger,
            ): endpoint["endpoint_uuid"]
            for endpoint in active_endpoints
        }

        account_futures = {
            executor.submit(
                _get_endpoint_accounts,
                endpoint["endpoint_uuid"],
                globus_compute_client,
                accounts_func_id,
                logger,
            ): endpoint["endpoint_uuid"]
            for endpoint in active_endpoints
        }

        # Process partition results as they complete
        for future in concurrent.futures.as_completed(partition_futures):
            try:
                endpoint_uuid, partition_list = future.result()
                database.save_partition(
                    identity_id=identity_id,
                    endpoint_uuid=endpoint_uuid,
                    partitions=partition_list,
                )
            except Exception as e:
                logger.error(f"Error processing partitions: {e}")

        # Process account results as they complete
        for future in concurrent.futures.as_completed(account_futures):
            try:
                endpoint_uuid, account_list = future.result()
                database.save_accounts(
                    identity_id=identity_id,
                    endpoint_uuid=endpoint_uuid,
                    accounts=account_list,
                )
            except Exception as e:
                logger.error(f"Error processing accounts: {e}")

    return True
