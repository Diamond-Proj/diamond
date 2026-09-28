"""Task status vocabulary and the values derived from it."""

from datetime import datetime, timedelta

# Statuses sacct will never tell us anything new about.
TERMINAL_STATES = frozenset({"COMPLETED", "COMPLETING", "FAILED", "MISSING"})

# Derived, never written to the database, and deliberately not in
# TERMINAL_STATES: it is a display and polling hint, not a record of what the
# job did. Because it is derived it also un-sets itself the moment a real status
# arrives.
STALE_STATUS = "STALE"

# A non-terminal task older than this never reported a final state
# Stop polling for it after this time.
STALE_AFTER = timedelta(days=4)


def normalize_status(raw_status) -> str:
    """Fold NULL / whitespace / case variants into one comparable token."""
    return str(raw_status or "").strip().upper()


def is_terminal(raw_status) -> bool:
    return normalize_status(raw_status) in TERMINAL_STATES


def task_age(task, *, now=None) -> timedelta | None:
    """Age of a task, or None when it cannot be computed.

    task_create_time is a nullable column, and this sits behind four endpoints on
    a 10s poll, so a NULL has to degrade to "unknown" rather than 500.
    """
    created = task.task_create_time
    if created is None:
        return None
    # Matching created's tzinfo keeps the subtraction valid whether rows are
    # naive or aware, without asserting which they are.
    age = (now or datetime.now(created.tzinfo)) - created
    return age if age >= timedelta(0) else timedelta(0)


def is_stale(task, *, now=None) -> bool:
    # Terminal first: a finished job's status is final however old it is.
    if is_terminal(task.task_status):
        return False
    age = task_age(task, now=now)
    if age is None:
        return False  # unknown age -> keep polling rather than invent a state
    return age >= STALE_AFTER


def effective_status(task, *, now=None) -> str:
    """The status to display and branch on. Derived; never persisted."""
    if is_stale(task, now=now):
        return STALE_STATUS
    return normalize_status(task.task_status)
