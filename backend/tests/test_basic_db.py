def test_basic(test_db, test_identity):
    assert test_db
    endpoints = test_db.get_endpoints(test_identity)
    assert len(endpoints) >= 3

    endpoint_statuses = [ep.endpoint_status for ep in endpoints]
    assert "online" in endpoint_statuses
    assert "offline" in endpoint_statuses
