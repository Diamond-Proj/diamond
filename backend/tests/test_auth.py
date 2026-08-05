def test_auth_mocking(client):
    """Confirm that the authenticated wrappers are mocked appropriately"""
    result = client.get("/api/is_authenticated")
    assert result.status_code == 200
    assert result.json["is_authenticated"] is True
