from unittest.mock import patch


def test_healthcheck_healthy(client):
    """Test healthcheck endpoint returns healthy status when git info is available."""
    with patch("app.routes.get_git_info") as mock_git_info:
        mock_git_info.return_value = {
            "commit_sha": "a1b2c3d4e5f6789abcdef1234567890abcdef123"
        }

        response = client.get("/api/healthcheck")

        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "git" in data
        assert data["git"]["commit_sha"] == "a1b2c3d4e5f6789abcdef1234567890abcdef123"


def test_healthcheck_unhealthy(client):
    """Test healthcheck endpoint returns unhealthy status when git info is unknown."""
    with patch("app.routes.get_git_info") as mock_git_info:
        mock_git_info.return_value = {"commit_sha": "unknown"}

        response = client.get("/api/healthcheck")

        assert response.status_code == 500

        data = response.get_json()
        assert data["status"] == "unhealthy"
        assert "timestamp" in data
        assert "git" in data
        assert data["git"]["commit_sha"] == "unknown"
