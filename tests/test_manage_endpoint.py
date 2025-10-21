# from flask import Flask, g, jsonify
# Assuming your Flask app is defined in app.py


import pytest

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
