import logging
from unittest import mock
from unittest.mock import patch


def test_get_partitions(client, monkeypatch):
    # mock_db = mock.Mock(Database)

    with patch("diamond_backend.app.g_database") as mock_db:
        mock_db.get_partitions = mock.Mock(return_value=["DEBUG", "PROD"])

        # monkeypatch.setattr("diamond_backend.app.database", mock_db)
        response = client.post(
            "/api/list_partitions", json={"endpoint": "TEST_ENDPOINT"}
        )
        logging.warning(f"YADU: {response=}")


"""
def test_nonexistent_partitions(client):

    response = client.post("/api/list_partitions", json={"endpoint": "TEST_ENDPOINT"})
    assert response.status_code == 200
    assert response.json is None

"""
