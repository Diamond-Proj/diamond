"""Waiting on Globus Compute task results inside an HTTP request."""

import logging
import time
from typing import Any, Tuple

from globus_compute_sdk import Client as GlobusComputeClient
from globus_compute_sdk.errors import TaskPending

from diamond_backend.app.database.data_manager import Database
from diamond_backend.app.utils.errors import ComputeTaskFailed, ComputeTaskTimeout

# Deadline for waiting on a Compute result inside an HTTP request: the budget
# job submission already had (sleeps of 0..11 s, 66 s in total). Only short
# control tasks (sbatch, path setup, metadata) wait inline; long work runs as a
# Slurm job and is polled. Note that Gunicorn's default 30 s worker timeout and
# the ALB's 60 s idle timeout are shorter than this deadline.
COMPUTE_RESULT_TIMEOUT_S = 66.0
_POLL_INITIAL_DELAY_S = 1.0
_POLL_MAX_DELAY_S = 8.0
_POLL_BACKOFF = 1.5


def describe_task_owner(
    database: Database, identity_id: str, endpoint_uuid: str
) -> Tuple[str | None, str | None]:
    """Return (endpoint name, username) to label a Compute task's log lines.

    Diamond stores no Globus username, so the profile email stands in for it.
    """
    profile = database.load_profile(identity_id)
    return (
        database.get_endpoint_name(identity_id, endpoint_uuid),
        profile.email if profile else None,
    )


def wait_for_compute_result(
    globus_compute_client: GlobusComputeClient,
    task_id: str,
    endpoint_id: str,
    logger: logging.Logger,
    timeout_s: float = COMPUTE_RESULT_TIMEOUT_S,
    *,
    endpoint_name: str | None = None,
    username: str | None = None,
) -> Any:
    """Poll a Compute task until it returns, fails, or the deadline passes.

    Raises ComputeTaskTimeout (504) or ComputeTaskFailed (502).
    """
    owner = f"endpoint {endpoint_id} ({endpoint_name}), user {username}"
    start = time.monotonic()
    deadline = start + timeout_s
    delay = _POLL_INITIAL_DELAY_S
    while True:
        try:
            result = globus_compute_client.get_result(task_id)
        except TaskPending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.warning(
                    "Compute task %s on %s still pending after %.1fs; giving up.",
                    task_id,
                    owner,
                    time.monotonic() - start,
                )
                raise ComputeTaskTimeout(task_id, endpoint_id, timeout_s)
            time.sleep(min(delay, remaining))
            delay = min(delay * _POLL_BACKOFF, _POLL_MAX_DELAY_S)
        except Exception as exc:
            # TaskExecutionFailed can stringify to "", so log type and repr.
            logger.error(
                "Compute task %s on %s failed after %.1fs: %s %r",
                task_id,
                owner,
                time.monotonic() - start,
                type(exc).__name__,
                exc,
            )
            raise ComputeTaskFailed(task_id, endpoint_id, exc) from exc
        else:
            logger.info(
                "Compute task %s on %s returned after %.1fs.",
                task_id,
                owner,
                time.monotonic() - start,
            )
            return result
