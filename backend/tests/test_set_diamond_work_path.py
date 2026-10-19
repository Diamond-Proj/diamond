import os
import posixpath
from unittest.mock import patch

import pytest

from diamond_backend.app import app
from diamond_backend.app.errors import RequestMalformed
from diamond_backend.app.utils.errors import InvalidWorkPath
from diamond_backend.app.utils.work_path import (
    normalize_work_path,
    resolve_diamond_dirs,
)


@pytest.fixture
def client(test_identity):
    app.config["TESTING"] = True
    with app.test_client() as client:
        client.set_cookie("primary_identity", test_identity)
        client.set_cookie("tokens", "TEST_TOKENS")
        yield client


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("/u/username", "/u/username"),
        ("/projects/proj/username/runs", "/projects/proj/username/runs"),
        ("/work/nvme/proj/username/", "/work/nvme/proj/username"),
        ("/scratch/username", "/scratch/username"),
        ("  /scratch/username  ", "/scratch/username"),
        ("/u/username//a/./b/", "/u/username/a/b"),
        ("//u/username", "/u/username"),
    ],
)
def test_normalize_work_path_accepts_any_absolute_path(raw, expected):
    assert normalize_work_path(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "   ", 42, ["/u/username"]])
def test_normalize_work_path_rejects_missing(raw):
    with pytest.raises(RequestMalformed):
        normalize_work_path(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "~",
        "~/diamond",
        "~username/x",
        "u/username",
        "./x",
        "/",
        "//",
        "/..",
        "/u/username/..",
        "/u/username/a/../b",
        "/scratch/user\x00/diamond",
        "/scratch/user/diamond\x00",
    ],
)
def test_normalize_work_path_rejects_invalid(raw):
    with pytest.raises(InvalidWorkPath):
        normalize_work_path(raw)


def test_normalize_work_path_rejects_dotdot_after_symlink(tmp_path):
    """`link/..` is the symlink target's parent, not the lexical parent.

    A lexical normpath would silently select a different, possibly existing and
    writable, directory than the one the endpoint would resolve.
    """
    (tmp_path / "scratch" / "project" / "run").mkdir(parents=True)
    (tmp_path / "scratch" / "project" / "work").mkdir()
    (tmp_path / "home" / "user" / "work").mkdir(parents=True)
    (tmp_path / "home" / "user" / "link").symlink_to(
        tmp_path / "scratch" / "project" / "run"
    )
    raw = f"{tmp_path}/home/user/link/../work"

    # Premise: the filesystem and a lexical normalization disagree.
    assert os.path.realpath(raw) == os.path.realpath(
        tmp_path / "scratch" / "project" / "work"
    )
    assert posixpath.normpath(raw) == f"{tmp_path}/home/user/work"

    with pytest.raises(InvalidWorkPath):
        normalize_work_path(raw)


@pytest.mark.parametrize(
    "work_path, diamond_dir",
    [
        ("/u/username", "/u/username/diamond"),
        ("/u/username/diamond", "/u/username/diamond"),
        # Only an exact final component counts; suffixes do not.
        ("/projects/proj-diamond", "/projects/proj-diamond/diamond"),
        ("/scratch/username/mydiamond", "/scratch/username/mydiamond/diamond"),
        ("/projects/diamond/username", "/projects/diamond/username/diamond"),
    ],
)
def test_resolve_diamond_dirs(work_path, diamond_dir):
    assert resolve_diamond_dirs(work_path) == (
        diamond_dir,
        f"{diamond_dir}/logs",
        f"{diamond_dir}/images",
    )


@pytest.mark.parametrize(
    "kwargs, code",
    [
        ({"data": "not json", "content_type": "text/plain"}, "REQUEST_MALFORMED"),
        ({"json": ["/u/username"]}, "REQUEST_MALFORMED"),
        ({"json": {"diamond_work_path": "/u/username"}}, "REQUEST_MALFORMED"),
        (
            {"json": {"endpoint_uuid": " ", "diamond_work_path": "/u/username"}},
            "REQUEST_MALFORMED",
        ),
        ({"json": {"endpoint_uuid": "EP"}}, "REQUEST_MALFORMED"),
        (
            {"json": {"endpoint_uuid": "EP", "diamond_work_path": "~/diamond"}},
            "INVALID_WORK_PATH",
        ),
        (
            {"json": {"endpoint_uuid": "EP", "diamond_work_path": "u/username"}},
            "INVALID_WORK_PATH",
        ),
        (
            {"json": {"endpoint_uuid": "EP", "diamond_work_path": "/u/link/../x"}},
            "INVALID_WORK_PATH",
        ),
        (
            {
                "data": '{"endpoint_uuid": "EP", '
                '"diamond_work_path": "/scratch/user\\u0000/diamond"}',
                "content_type": "application/json",
            },
            "INVALID_WORK_PATH",
        ),
    ],
)
def test_set_diamond_work_path_rejects_bad_request(client, kwargs, code):
    with patch(
        "diamond_backend.app.endpoints.initialize_globus_compute_client"
    ) as init_client:
        response = client.post("/api/set_diamond_work_path", **kwargs)

    assert response.status_code == 400, response.get_data(as_text=True)
    assert response.get_json()["code"] == code
    init_client.assert_not_called()
