import os
from urllib.parse import urljoin, urlparse

import globus_sdk
from flask import current_app, request


def get_git_info():
    """Get the latest git commit SHA and commit time from the main branch."""
    # Check if RAILWAY_GIT_COMMIT_SHA exists and is a string
    railway_commit_sha = current_app.config.get("RAILWAY_GIT_COMMIT_SHA")
    if (
        railway_commit_sha
        and isinstance(railway_commit_sha, str)
        and len(railway_commit_sha) == 40
    ):
        return {"commit_sha": railway_commit_sha}
    else:
        return {"commit_sha": "unknown"}


def load_portal_client():
    """Create an AuthClient for the portal"""
    return globus_sdk.ConfidentialAppAuthClient(
        os.environ["PORTAL_CLIENT_ID"], os.environ["PORTAL_CLIENT_SECRET"]
    )


def is_safe_redirect_url(target):
    """https://security.openstack.org/guidelines/dg_avoid-unvalidated-redirects.html"""  # noqa
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))

    return (
        redirect_url.scheme in ("http", "https")
        and host_url.netloc == redirect_url.netloc
    )


def get_safe_redirect():
    """https://security.openstack.org/guidelines/dg_avoid-unvalidated-redirects.html"""  # noqa
    url = request.args.get("next")
    if url and is_safe_redirect_url(url):
        return url

    url = request.referrer
    if url and is_safe_redirect_url(url):
        return url

    return "/"
