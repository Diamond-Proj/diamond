import json

import pytest

from diamond_backend.app import app


@pytest.fixture
def client():
    """Test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_cookies():
    """Mock request cookies."""
    return {
        "primary_identity": "test-user-id",
        "tokens": json.dumps(
            {
                "transfer.api.globus.org": {
                    "scope": "urn:globus:auth:scope:transfer.api.globus.org:all",
                    "access_token": "mock-access-token",
                }
            }
        ),
    }
