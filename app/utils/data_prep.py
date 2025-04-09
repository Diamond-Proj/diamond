import time

from .parsers import resolve_host
from .functions import (
    get_partitions,
    get_accounts,
)


def register_active_endpoints(globus_compute_client, identity_id, database, logger):
    logger.info(f"Registering active endpoints for user: {identity_id}")
    endpoints = globus_compute_client.get_endpoints()
    for endpoint in endpoints:
        logger.info(f"Checking endpoint: {endpoint}")
        endpoint_name = endpoint["name"]
        endpoint_uuid = endpoint["uuid"]
        try:
            endpoint_status = globus_compute_client.get_endpoint_status(
                endpoint_uuid=endpoint_uuid
            )["status"]
        except Exception as e:
            logger.error(f"Error getting endpoint status for endpoint {endpoint_name}: {e}")
            continue
        if endpoint_status == "online":
            endpoint_metadata = globus_compute_client.get_endpoint_metadata(
                endpoint_uuid=endpoint_uuid)
            endpoint_host = resolve_host(endpoint_metadata["hostname"])
            if not database.exists_endpoint(endpoint_uuid=endpoint_uuid):
                logger.info(f"Saving endpoint: {endpoint_uuid}")
                database.save_endpoint(
                    identity_id=identity_id,
                    endpoint_name=endpoint_name,
                    endpoint_host=endpoint_host,
                    endpoint_uuid=endpoint_uuid,
                )
    return

def load_endpoints_partitions(globus_compute_client, identity_id, database, logger):
    endpoints = database.get_endpoints(identity_id=identity_id)
    get_partitions_func_id = globus_compute_client.register_function(get_partitions)
    for endpoint in endpoints:
        endpoint_uuid = endpoint.endpoint_uuid
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
        partition_list = partitions_output.split("\n")
        for partition in partition_list:
            if not partition:
                partition_list.remove(partition)
        logger.info(f"Partitions output: {partition_list}")
        database.save_partition(
            identity_id=identity_id,
            endpoint_uuid=endpoint_uuid,
            partitions=partition_list,
        )
    return

def load_endpoints_accounts(globus_compute_client, identity_id, database, logger):
    endpoints = database.get_endpoints(identity_id=identity_id)
    accounts_func_id = globus_compute_client.register_function(get_accounts)
    for endpoint in endpoints:
        endpoint_uuid = endpoint.endpoint_uuid
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
        account_list = accounts_output.split("\n")
        for account in account_list:
            if not account:
                account_list.remove(account)
        logger.info(f"Accounts output: {account_list}")
        database.save_accounts(
            identity_id=identity_id,
            endpoint_uuid=endpoint_uuid,
            accounts=account_list,
        )
    return
