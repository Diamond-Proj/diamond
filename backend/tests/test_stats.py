def test_stats(test_db, test_identity):
    stats = test_db.get_stats(identity_id=test_identity)
    assert stats

    assert "endpoints" in stats
    assert stats["endpoints"]["online"] == 2, "Expected 2 online EPs"
    assert stats["endpoints"]["offline"] == 1, "Expected 1 offline EP"

    assert "datasets" in stats
    assert stats["datasets"]["public"] == 1, "Expected 1 public dataset"
    assert stats["datasets"]["private"] == 2, "Expected 2 private dataset"

    assert "images" in stats
    assert stats["images"]["public"] == 0, "Expected 1 public image"
    assert stats["images"]["private"] == 3, "Expected 2 private image"

    assert "recent_tasks" in stats
