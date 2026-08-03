import logging
import random

from diamond_backend.app.database.data_manager import Database


def test_new_profile(test_db: Database):
    """Confirm that new users are not initialized by default"""
    assert test_db
    test_id = f"TEST_IDENTITY_{random.randint(1, 100)}"
    test_db.save_profile(test_id, "Bob", "bob@tester.org")

    identity = test_db.load_profile(test_id)
    assert identity.identity_id == test_id
    assert not identity.is_initialized, "Bob should not be initialized"

    test_db.set_profile_initialization_state(test_id, initialized=True)

    identity = test_db.load_profile(test_id)
    logging.warning(f"Identity : {identity.is_initialized=}")

    assert identity.is_initialized, "Bob should be initialized here"


def test_new_profile_init(test_db: Database):
    assert test_db
    test_id = f"TEST_IDENTITY_{random.randint(1, 100)}"
    test_db.save_profile(test_id, "Jack", "jack@tester.org", is_initialized=True)

    identity = test_db.load_profile(test_id)
    assert identity.identity_id == test_id
    assert identity.is_initialized, "Jack should be initialized"
