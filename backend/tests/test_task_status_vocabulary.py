"""Unit tests for the derived task status vocabulary.

These exercise diamond_backend.app.utils.task_status directly with lightweight
stand-ins rather than ORM rows -- every function there takes anything with
task_status / task_create_time attributes.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from diamond_backend.app.utils.task_status import (
    STALE_AFTER,
    STALE_STATUS,
    effective_status,
    is_stale,
    is_terminal,
    normalize_status,
    task_age,
)


def make_task(task_status="PENDING", age=None, created=None):
    if created is None and age is not None:
        created = datetime.now() - age
    return SimpleNamespace(task_status=task_status, task_create_time=created)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("COMPLETED", "COMPLETED"),
        ("  completed  ", "COMPLETED"),
        ("Running", "RUNNING"),
        (None, ""),
        ("", ""),
    ],
)
def test_normalize_status(raw, expected):
    assert normalize_status(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("COMPLETED", True),
        ("completing", True),
        ("FAILED", True),
        ("MISSING", True),
        ("PENDING", False),
        ("RUNNING", False),
        (None, False),
        (STALE_STATUS, False),  # derived, never authoritative
    ],
)
def test_is_terminal(raw, expected):
    assert is_terminal(raw) is expected


def test_terminal_task_is_never_stale():
    """A job that finished long ago must keep its real status.

    We know exactly what happened to it, so age says nothing. If this inverts,
    every task completed over STALE_AFTER ago is relabelled STALE.
    """
    task = make_task("COMPLETED", age=STALE_AFTER * 3)
    assert is_stale(task) is False
    assert effective_status(task) == "COMPLETED"


def test_old_unfinished_task_is_stale():
    task = make_task("PENDING", age=STALE_AFTER + timedelta(days=1))
    assert is_stale(task) is True
    assert effective_status(task) == STALE_STATUS


@pytest.mark.parametrize(
    "age,expected_stale",
    [
        (STALE_AFTER - timedelta(days=1), False),
        (STALE_AFTER + timedelta(seconds=1), True),
    ],
)
def test_stale_boundary(age, expected_stale):
    assert is_stale(make_task("RUNNING", age=age)) is expected_stale


def test_missing_create_time_is_not_stale():
    """Unknown age means keep polling, never invent a terminal-looking state."""
    task = make_task("PENDING", created=None)
    assert task_age(task) is None
    assert is_stale(task) is False
    assert effective_status(task) == "PENDING"


@pytest.mark.parametrize(
    "created",
    [
        datetime.now() - timedelta(days=1),
        datetime.now(timezone.utc) - timedelta(days=1),
    ],
    ids=["naive", "aware"],
)
def test_task_age_handles_naive_and_aware(created):
    """Must not raise on either; rows are naive today and may become aware."""
    age = task_age(make_task("RUNNING", created=created))
    assert timedelta(hours=23) < age < timedelta(hours=25)


def test_future_create_time_clamps_to_zero():
    task = make_task("RUNNING", created=datetime.now() + timedelta(days=2))
    assert task_age(task) == timedelta(0)
    assert is_stale(task) is False


def test_now_override_is_honoured():
    created = datetime(2025, 1, 1, 12, 0, 0)
    task = make_task("PENDING", created=created)
    assert task_age(task, now=created + timedelta(days=30)) == timedelta(days=30)
    assert is_stale(task, now=created + timedelta(days=30)) is True
    assert is_stale(task, now=created + timedelta(days=1)) is False
