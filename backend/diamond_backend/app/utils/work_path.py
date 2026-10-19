"""Validation and layout of the user-entered Diamond work path."""

import posixpath

from diamond_backend.app.errors import RequestMalformed
from diamond_backend.app.utils.errors import InvalidWorkPath

DIAMOND_DIR_NAME = "diamond"


def normalize_work_path(raw_path: object) -> str:
    """Validate a user-entered work path and return its normalized form.

    The path is resolved on the remote endpoint, so any absolute POSIX path is
    accepted (home, project, work or scratch filesystems alike). `~` is rejected
    because only the worker, not the backend, could expand it.
    """
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise RequestMalformed("diamond_work_path")
    path = raw_path.strip()
    if path.startswith("~"):
        raise InvalidWorkPath(
            "Work path must be absolute; '~' is not expanded. "
            "Enter the full path, e.g. /u/<username>.",
            raw_path,
        )
    if not posixpath.isabs(path):
        raise InvalidWorkPath(
            f"Work path must be an absolute path starting with '/': {path}",
            raw_path,
        )
    # Reject "..": through a symlink it is the target's parent, not the lexical one.
    if ".." in path.split("/"):
        raise InvalidWorkPath(
            f"Work path must not contain '..' components: {path}",
            raw_path,
        )
    # Safe without "..". normpath keeps a leading "//", so strip it too.
    normalized = "/" + posixpath.normpath(path).lstrip("/")
    if normalized == "/":
        raise InvalidWorkPath("Work path cannot be the filesystem root.", raw_path)
    return normalized


def resolve_diamond_dirs(work_path: str) -> tuple[str, str, str]:
    """Return (diamond_dir, log_dir, image_dir) for a normalized work path.

    The API accepts either the work root or the final `diamond` directory: only
    a last path component that is exactly `diamond` is treated as the latter.
    """
    if posixpath.basename(work_path) == DIAMOND_DIR_NAME:
        diamond_dir = work_path
    else:
        diamond_dir = posixpath.join(work_path, DIAMOND_DIR_NAME)
    return (
        diamond_dir,
        posixpath.join(diamond_dir, "logs"),
        posixpath.join(diamond_dir, "images"),
    )
