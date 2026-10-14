import logging
import random
import uuid
from unittest.mock import Mock

import pytest
from globus_compute_sdk.sdk.client import Client

from diamond_backend.app.errors import EndpointNotFound
from diamond_backend.app.utils.data_prep import (
    endpoint_initialization_status,
    refresh_managed_endpoints,
)
from tests.conftest import TEST_IDENTITY


@pytest.fixture
def mock_gc_client(
    test_identity, test_endpoint_anvil, test_endpoint_delta, test_endpoint_frontera
):
    mock_gc_client = Mock(spec=Client)

    mock_ep_list = [
        {
            "uuid": test_endpoint_anvil[2],
            "name": test_endpoint_anvil[0],
            "display_name": test_endpoint_anvil[0],
            "owner": TEST_IDENTITY,
        },
        {
            "uuid": test_endpoint_delta[2],
            "name": test_endpoint_delta[0],
            "display_name": test_endpoint_delta[0],
            "owner": TEST_IDENTITY,
        },
        {
            "uuid": test_endpoint_frontera[2],
            "name": test_endpoint_frontera[0],
            "display_name": test_endpoint_frontera[0],
            "owner": TEST_IDENTITY,
        },
        {
            "uuid": str(uuid.uuid4()),
            "name": "NON_MANAGED_1",
            "display_name": "NON_MANAGED_1",
            "owner": TEST_IDENTITY,
        },
    ]
    mock_gc_client.get_endpoints.return_value = mock_ep_list
    return mock_gc_client


def test_is_managed_from_db(test_identity, test_db):
    """Confirm that there are 2 managed and 1 non-managed EPs in DB"""
    endpoints = test_db.get_endpoints(identity_id=TEST_IDENTITY)
    assert len(endpoints) == 3
    assert sum([ep.is_managed for ep in endpoints]) == 2, "Expected 2 managed endpoints"


def test_list_endpoints(test_db, mock_gc_client):
    eps = endpoint_initialization_status(
        mock_gc_client, identity_id=TEST_IDENTITY, database=test_db
    )
    assert len(eps) == len(mock_gc_client.get_endpoints.return_value)
    assert isinstance(eps, dict)

    assert sum([1 for ep in eps.values() if ep["is_managed"]]) == 2
    assert sum([1 for ep in eps.values() if not ep["is_managed"]]) == 2

    for ep in eps.values():
        if ep["name"] == "NON_MANAGED_1":
            assert ep["is_managed"] is False


def test_flipping_managed_status(test_db, test_identity):
    first_ep = test_db.get_endpoints(identity_id=test_identity)[0]

    assert isinstance(first_ep.is_managed, bool)

    original_status = first_ep.is_managed
    original_ep = first_ep.endpoint_uuid

    test_db.update_endpoint_managed_status(
        first_ep.identity_id,
        first_ep.endpoint_uuid,
        is_managed=not first_ep.is_managed,
    )

    first_ep = test_db.get_endpoints(identity_id=test_identity)[0]

    assert first_ep.is_managed is not original_status
    assert first_ep.endpoint_uuid == original_ep

    # Revert changes after testing
    test_db.update_endpoint_managed_status(
        first_ep.identity_id,
        first_ep.endpoint_uuid,
        is_managed=original_status,
    )


def test_non_existent_manager_update(test_db, test_identity):
    with pytest.raises(EndpointNotFound):
        test_db.update_endpoint_managed_status(
            test_identity,
            "BAD_UUID",
            is_managed=True,
        )


def test_refresh_only_polls_managed_endpoints(test_db):
    """Refresh must not touch endpoints the user has not added to management."""
    identity = f"TEST_IDENTITY_REFRESH_{random.randint(1, 100000)}"
    managed_uuid = str(uuid.uuid4())
    unmanaged_uuid = str(uuid.uuid4())
    test_db.save_endpoint(
        identity, "MANAGED_EP", "host", managed_uuid, "offline", is_managed=True
    )
    test_db.save_endpoint(identity, "UNMANAGED_EP", "host", unmanaged_uuid, "offline")
    # Same (shared MEP) uuid managed by another user must stay untouched.
    other_identity = f"{identity}_OTHER"
    test_db.save_endpoint(
        other_identity, "MANAGED_EP", "host", managed_uuid, "offline", is_managed=True
    )

    client = Mock(spec=Client)
    client.get_endpoint_status.return_value = {"status": "online"}
    refresh_managed_endpoints(client, identity, test_db, logging.getLogger(__name__))

    client.get_endpoint_status.assert_called_once_with(endpoint_uuid=managed_uuid)
    statuses = {
        ep.endpoint_uuid: ep.endpoint_status
        for ep in test_db.get_endpoints(identity_id=identity)
    }
    assert statuses == {managed_uuid: "online", unmanaged_uuid: "offline"}
    other_row = test_db.get_endpoints(identity_id=other_identity)[0]
    assert other_row.endpoint_status == "offline"

    test_db.delete_endpoints(identity)
    test_db.delete_endpoints(other_identity)
