import json
import uuid

import pytest

from diamond_backend.app import app, g_database
from diamond_backend.app.database.data_manager import Database

mock_token = {
    "auth.globus.org": {
        "access_token": "FAKE_TOKEN",
        "resource_server": "auth.globus.org",
        "token_type": "Bearer",
        "scope": "profile email openid",
    },
    "transfer.api.globus.org": {
        "access_token": "FAKE_TOKEN",
        "resource_server": "transfer.api.globus.org",
        "token_type": "Bearer",
        "scope": "urn:globus:auth:scope:transfer.api.globus.org:all",
    },
    "funcx_service": {
        "access_token": "FAKE_TOKEN",
        "refresh_token": None,
        "resource_server": "funcx_service",
        "token_type": "Bearer",
        "scope": "https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/all",
    },
}

TEST_IDENTITY = "TEST_IDENTITY_1"


@pytest.fixture(scope="session")
def test_identity():
    return TEST_IDENTITY


@pytest.fixture(scope="session")
def test_endpoint_anvil(test_identity) -> tuple:
    return ("TEST_EP1", "anvil.rcac.purdue.edu", str(uuid.uuid4()), "online")


@pytest.fixture(scope="session")
def test_endpoint_delta(test_identity) -> tuple:
    return ("TEST_EP2", "login.delta.ncsa.uiuc.edu", str(uuid.uuid4()), "online")


@pytest.fixture(scope="session")
def test_endpoint_frontera(test_identity) -> tuple:
    return ("TEST_EP3", "login.frontera.tacc.edu", str(uuid.uuid4()), "offline")


@pytest.fixture(scope="session", autouse=True)
def test_db(
    test_identity, test_endpoint_anvil, test_endpoint_delta, test_endpoint_frontera
) -> Database:
    with app.app_context():
        g_database.ensure_tables_exist()
        g_database.save_profile(test_identity, "Alice", "alice@tester.org")
        g_database.save_endpoint(test_identity, *test_endpoint_frontera)
        g_database.save_endpoint(test_identity, *test_endpoint_anvil)
        g_database.save_endpoint(test_identity, *test_endpoint_delta)
        g_database.update_endpoint_managed_status(
            test_identity, test_endpoint_anvil[2], is_managed=True
        )
        g_database.update_endpoint_managed_status(
            test_identity, test_endpoint_delta[2], is_managed=True
        )
        g_database.update_endpoint_managed_status(
            test_identity, test_endpoint_frontera[2], is_managed=False
        )

        g_database.save_container(identity_id=test_identity, name="TestContainer1")
        g_database.save_container(identity_id=test_identity, name="TestContainer2")
        g_database.save_container(identity_id=test_identity, name="TestContainer3")
        g_database.save_dataset(
            str(uuid.uuid4()),
            "globus_path",
            "system_path",
            "Anvil@RCAC",
            None,
            test_identity,
            public=False,
            dataset_name="Test_Data_1",
        )
        g_database.save_dataset(
            str(uuid.uuid4()),
            "globus_path",
            "system_path",
            "Anvil@RCAC",
            None,
            test_identity,
            public=False,
            dataset_name="Test_Data_2",
        )
        g_database.save_dataset(
            str(uuid.uuid4()),
            "globus_path",
            "system_path",
            "Anvil@RCAC",
            None,
            test_identity,
            public=True,
            dataset_name="Test_Data_3",
        )

        yield g_database
        # No cleanup necessary since we are writing to an in-memory db for tests


@pytest.fixture
def client(test_identity):
    """Test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        client.set_cookie("tokens", json.dumps(mock_token))
        client.set_cookie("primary_identity", test_identity)
        yield client
