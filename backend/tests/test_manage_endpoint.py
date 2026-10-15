# from flask import Flask, g, jsonify
# Assuming your Flask app is defined in app.py
import random
import uuid
from unittest.mock import Mock, patch

import pytest
from globus_compute_sdk.sdk.client import Client

from diamond_backend.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_update_endpoint_managed_status_success(
    client, test_identity, test_endpoint_anvil
):
    # test_db is required to force setup of DB for testing.
    endpoint_uuid = test_endpoint_anvil[2]

    client.set_cookie("primary_identity", test_identity)
    client.set_cookie("tokens", "TEST_TOKENS")
    response = client.put(
        f"/api/manage_endpoint/{endpoint_uuid}",
        json={"is_managed": False},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert endpoint_uuid in data["message"]
    assert data["new_status"] is False

    response = client.put(
        f"/api/manage_endpoint/{endpoint_uuid}",
        json={"is_managed": True},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert endpoint_uuid in data["message"]
    assert data["new_status"] is True


def test_update_endpoint_managed_status_missing_json_field(
    client, test_endpoint_anvil, test_identity
):
    endpoint_uuid = test_endpoint_anvil[2]

    client.set_cookie("primary_identity", test_identity)
    client.set_cookie("tokens", "TEST_TOKENS")

    # Expecting a RequestMalformed exception → 400 Bad Request
    response = client.put(
        f"/api/manage_endpoint/{endpoint_uuid}",
        json={},  # Missing "is_managed"
    )

    assert response.status_code == 400
    assert response.json["code"] == "REQUEST_MALFORMED"
    assert "Missing JSON field 'is_managed'" in response.json["reason"]


def test_user_init_on_endpoint_managed_status_set(
    test_db, client, test_endpoint_frontera, test_endpoint_anvil
):
    endpoint_uuid = test_endpoint_anvil[2]

    assert test_db
    test_id = f"TEST_IDENTITY_JOE_{uuid.uuid4().hex[:8]}"
    test_db.save_profile(test_id, "Joe", "joe@tester.org")

    identity = test_db.load_profile(test_id)
    assert identity.identity_id == test_id
    assert not identity.is_initialized, "Joe should not be initialized"
    # Test EP frontera is not initialized
    test_db.save_endpoint(test_id, *(test_endpoint_frontera))
    endpoint_uuid = test_endpoint_frontera[2]

    client.set_cookie("primary_identity", test_id)
    client.set_cookie("tokens", "TEST_TOKENS")
    response = client.put(
        f"/api/manage_endpoint/{endpoint_uuid}",
        json={"is_managed": True},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["new_status"] is True

    identity = test_db.load_profile(test_id)
    assert identity.identity_id == test_id
    assert identity.is_initialized, "Joe should be initialized"


def test_manage_endpoint_registers_unknown_endpoint(test_db, client):
    """A new user adds an endpoint before ever hitting Refresh: the row does
    not exist yet, so the PUT must register it instead of returning 404."""
    identity = f"TEST_IDENTITY_FRESH_{random.randint(1, 100000)}"
    endpoint_uuid = str(uuid.uuid4())
    test_db.save_profile(identity, "Fresh", "fresh@tester.org")
    assert test_db.get_endpoints(identity_id=identity) == []

    compute_client = Mock(spec=Client)
    compute_client.get_endpoint_status.return_value = {"status": "online"}
    compute_client.get_endpoint_metadata.return_value = {
        "display_name": "Fresh Endpoint",
        "hostname": "login.anvil.rcac.purdue.edu",
    }

    client.set_cookie("primary_identity", identity)
    client.set_cookie("tokens", "TEST_TOKENS")
    with patch(
        "diamond_backend.app.endpoints.initialize_globus_compute_client",
        return_value=compute_client,
    ):
        response = client.put(
            f"/api/manage_endpoint/{endpoint_uuid}",
            json={"is_managed": True},
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 200, response.get_json()
    assert response.get_json()["new_status"] is True

    endpoints = test_db.get_endpoints(identity_id=identity)
    assert len(endpoints) == 1
    saved = endpoints[0]
    assert saved.endpoint_uuid == endpoint_uuid
    assert saved.endpoint_name == "Fresh Endpoint"
    assert saved.endpoint_host == "Anvil@RCAC"
    assert saved.endpoint_status == "online"
    assert saved.is_managed is True

    test_db.delete_endpoints(identity)


def test_manage_endpoint_without_profile_still_succeeds(
    test_db, client, test_endpoint_anvil
):
    """The dashboard creates the profile lazily; a user who goes straight to
    /endpoints has none, and the PUT used to 500 after committing the flag."""
    identity = f"TEST_IDENTITY_NO_PROFILE_{random.randint(1, 100000)}"
    test_db.save_endpoint(identity, *test_endpoint_anvil)
    endpoint_uuid = test_endpoint_anvil[2]
    assert test_db.load_profile(identity) is None

    client.set_cookie("primary_identity", identity)
    client.set_cookie("tokens", "TEST_TOKENS")
    response = client.put(
        f"/api/manage_endpoint/{endpoint_uuid}",
        json={"is_managed": True},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_json()["new_status"] is True
    assert test_db.get_endpoints(identity_id=identity)[0].is_managed is True

    test_db.delete_endpoints(identity)
