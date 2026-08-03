from diamond_backend.app import g_database


def test_get_profile_returns_existing_profile(client, test_identity):
    response = client.get(f"/api/profile?identity_id={test_identity}")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["profile"]["identityId"] == test_identity
    assert payload["message"] == "Profile found"


def test_get_profile_uses_cookie_when_missing_identity(client):
    missing_identity = "UNKNOWN_PROFILE"
    client.set_cookie("primary_identity", missing_identity)

    response = client.get("/api/profile")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["profile"] is None
    assert payload["message"] == "Profile not found"


def test_post_profile_updates_existing_profile(client, test_identity, test_db):
    test_db.set_profile_initialization_state(test_identity, initialized=True)

    update_payload = {
        "identity_id": test_identity,
        "name": "Updated User",
        "email": "updated@example.com",
        "institution": "Updated Institute",
    }

    response = client.post("/api/profile", json=update_payload)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["profile"]["name"] == "Updated User"
    assert payload["profile"]["email"] == "updated@example.com"
    assert payload["profile"]["institution"] == "Updated Institute"
    assert payload["profile"]["is_initialized"] is True

    record = g_database.load_profile(test_identity)
    assert record.name == "Updated User"
    assert record.is_initialized is True
